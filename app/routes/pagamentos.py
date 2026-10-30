import hashlib
import time

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import APP_URL, META_CAPI_ACCESS_TOKEN, META_PIXEL_ID, MP_ACCESS_TOKEN, PLANOS_CONFIG
from app.database import get_db
from app.models import User as DBUser
from app.seguranca import get_current_user

router = APIRouter()


def enviar_purchase_meta(db_user, valor, payment_id, request: Request = None):
    """Envia o evento Purchase para o Meta via Conversions API (server-side),
    para que campanhas de Conversao no Ads Manager tenham um sinal real de venda.
    Sem META_PIXEL_ID e META_CAPI_ACCESS_TOKEN o envio e simplesmente pulado."""
    if not META_PIXEL_ID or not META_CAPI_ACCESS_TOKEN:
        return
    try:
        email_hash = hashlib.sha256(db_user.email.strip().lower().encode()).hexdigest() if db_user.email else None
        user_data = {}
        if email_hash:
            user_data["em"] = [email_hash]
        if request is not None:
            client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
            if client_ip:
                user_data["client_ip_address"] = client_ip.split(",")[0].strip()
            user_agent = request.headers.get("user-agent")
            if user_agent:
                user_data["client_user_agent"] = user_agent

        payload = {
            "data": [{
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "event_id": f"payment_{payment_id}",
                "action_source": "website",
                "event_source_url": f"{APP_URL}/app",
                "user_data": user_data,
                "custom_data": {
                    "currency": "BRL",
                    "value": valor
                }
            }]
        }
        resp = requests.post(
            f"https://graph.facebook.com/v19.0/{META_PIXEL_ID}/events",
            params={"access_token": META_CAPI_ACCESS_TOKEN},
            json=payload,
            timeout=10
        )
        if resp.status_code not in (200, 201):
            print(f"[ERRO] Meta CAPI respondeu {resp.status_code}: {resp.text}")
        else:
            print(f"[META CAPI] Evento Purchase enviado (payment_id={payment_id}, valor={valor})")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar evento Purchase pro Meta: {e}")


# Cria uma preferencia de pagamento DINAMICA e AUTENTICADA:
# cada pagamento nasce ja vinculado a quem esta logado.
@router.post("/criar-pagamento/{plano_id}")
def criar_pagamento(plano_id: str, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    if plano_id not in PLANOS_CONFIG:
        raise HTTPException(status_code=400, detail="Plano invalido")

    if not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MP_ACCESS_TOKEN nao configurado no servidor")

    db_user = db.query(DBUser).filter(DBUser.username == user).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    plano_info = PLANOS_CONFIG[plano_id]

    # external_reference usa EMAIL. Formato: {email}#{plano_id}  ex: fulano@gmail.com#kit_pro
    # Fallback: user_{id}_{plano_id} se email for null (contas antigas).
    if db_user.email:
        external_reference = f"{db_user.email}#{plano_id}"
    else:
        external_reference = f"user_{db_user.id}_{plano_id}"

    preference_payload = {
        "items": [{
            "title": plano_info["title"],
            "quantity": 1,
            "unit_price": plano_info["price"],
            "currency_id": "BRL"
        }],
        "external_reference": external_reference,
        "back_urls": {
            "success": f"{APP_URL}/app",
            "failure": f"{APP_URL}/app",
            "pending": f"{APP_URL}/app"
        },
        "auto_return": "approved",
        "notification_url": f"{APP_URL}/webhook"
    }

    if db_user.email:
        preference_payload["payer"] = {"email": db_user.email}

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.mercadopago.com/checkout/preferences",
            json=preference_payload,
            headers=headers,
            timeout=15
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Falha ao conectar com Mercado Pago: {str(e)}")

    if response.status_code not in (200, 201):
        print(f"[ERRO MP] {response.status_code} - {response.text}")
        raise HTTPException(status_code=502, detail="Erro ao criar preferencia de pagamento")

    data = response.json()
    return {
        "init_point": data.get("init_point"),
        "preference_id": data.get("id")
    }


# O webhook nao confia no corpo da notificacao: sempre consulta o pagamento
# direto na API do Mercado Pago antes de liberar qualquer plano.
@router.post("/webhook")
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
        event_type = payload.get("action") or payload.get("type")

        if event_type in ["payment.created", "payment.updated", "payment"]:
            data = payload.get("data", {})
            payment_id = str(data.get("id") or payload.get("id") or "")
            if not payment_id.isdigit():
                print(f"[AVISO] Webhook com payment_id invalido: {payment_id!r}")
                return {"status": "ignored"}

            print(f"\n[MERCADO PAGO] Notificacao recebida! Consultando ID: {payment_id}...")

            headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
            url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
            mp_response = requests.get(url, headers=headers, timeout=15)

            if mp_response.status_code == 200:
                payment_data = mp_response.json()
                status = payment_data.get("status")

                if status == "approved":
                    external_ref = (payment_data.get("external_reference") or "").strip()
                    payer_email = (payment_data.get("payer") or {}).get("email")

                    db_user = None
                    plano_id_extraido = None

                    # 1) Formato atual: {email}#{plano_id}
                    if "#" in external_ref and "@" in external_ref:
                        email_ref, _, plano_id_extraido = external_ref.partition("#")
                        db_user = db.query(DBUser).filter(DBUser.email == email_ref).first()

                    # 2) Formato legado: user_{id}_{plano_id}
                    if not db_user and external_ref.startswith("user_"):
                        partes = external_ref.split("_")
                        if len(partes) >= 3:
                            try:
                                user_id = int(partes[1])
                                plano_id_extraido = "_".join(partes[2:])
                                db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
                                if db_user:
                                    print(f"[AVISO] Webhook usou user_id legado ({external_ref}).")
                            except ValueError:
                                db_user = None

                    # 3) Formato antigo: external_reference = "kit_pro" direto
                    if not db_user and external_ref in PLANOS_CONFIG:
                        plano_id_extraido = external_ref

                    # 4) Fallback: buscar por e-mail do pagador no MP
                    if not db_user and payer_email:
                        db_user = db.query(DBUser).filter(DBUser.email == payer_email).first()
                        if db_user:
                            print(f"[AVISO] Identificado por fallback de e-mail ({payer_email}), nao por external_reference.")

                    if db_user:
                        plano_final = PLANOS_CONFIG.get(plano_id_extraido, {}).get("plano_interno")
                        if not plano_final:
                            print(f"[ERRO] plano_id_extraido '{plano_id_extraido}' nao reconhecido em PLANOS_CONFIG. "
                                  f"Pagamento {payment_id} NAO foi liberado automaticamente. Verificar manualmente no painel do Mercado Pago.")
                        else:
                            db_user.plano = plano_final
                            db.commit()
                            print(f"[SUCESSO] Plano '{plano_final}' liberado para user_id={db_user.id} (username={db_user.username})")
                            valor_pago = PLANOS_CONFIG.get(plano_id_extraido, {}).get("price", 0)
                            enviar_purchase_meta(db_user, valor_pago, payment_id, request)
                    else:
                        print(f"[ERRO] Pagamento {payment_id} aprovado mas NAO foi possivel identificar o usuario. "
                              f"external_reference='{external_ref}' payer_email='{payer_email}'. "
                              f"Verificar manualmente no painel do Mercado Pago.")
                else:
                    print(f"[AGUARDANDO] O pagamento {payment_id} esta com status: {status}")
            else:
                print(f"[ERRO] Falha ao consultar o Mercado Pago: {mp_response.text}")

        return {"status": "ok"}

    except Exception as e:
        print(f"[ERRO GRAVE] Falha ao processar webhook: {str(e)}")
        return {"status": "error"}
