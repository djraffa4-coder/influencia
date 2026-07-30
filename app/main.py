from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import os
import hashlib
import time
import requests
from app.database import Base, engine, SessionLocal
from app.models import User as DBUser
from app.routes.auth import router as script_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


from fastapi.responses import RedirectResponse

@app.get("/")
@app.head("/")
def raiz():
    return RedirectResponse(url="/app")

@app.get("/app")
@app.head("/app")
def frontend():
    return FileResponse("static/index.html")

@app.get("/config-publica")
def config_publica():
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "meta_pixel_id": os.getenv("META_PIXEL_ID", ""),
        "tiktok_pixel_id": os.getenv("TIKTOK_PIXEL_ID", "")
    }

@app.get("/privacidade")
def privacidade():
    return FileResponse("static/privacidade.html")

@app.get("/termos")
def termos():
    return FileResponse("static/termos.html")

Base.metadata.create_all(bind=engine)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── SECRET_KEY: OBRIGATORIA via variavel de ambiente. ──
# Como este repositorio e PUBLICO, jamais use um valor padrao aqui no codigo -
# qualquer fallback fixo seria visivel a qualquer pessoa e permitiria forjar tokens.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY nao configurada! Configure a variavel de ambiente no Render.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias

oauth2_scheme = HTTPBearer()

# Access Token de Producao do Mercado Pago (variavel de ambiente, ja existente)
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# ── NOVO: URL base da sua aplicacao no Render ──
# Ex: APP_URL = https://influencia.onrender.com
# Sem barra no final. Usado pros back_urls e notification_url do Mercado Pago.
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

# ── NOVO: Brevo (API HTTP) para envio de emails (redefinicao de senha) ──
# SMTP e bloqueado no Render free tier, por isso usamos API HTTP em vez de smtplib.
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "djraffa4@gmail.com")

# ── NOVO: Google OAuth (login com Google) ──
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# ── ADMIN_KEY: OBRIGATORIA via env var - repo publico, sem fallback fixo. ──
ADMIN_KEY = os.getenv("ADMIN_KEY")
if not ADMIN_KEY:
    raise RuntimeError("ADMIN_KEY nao configurada! Configure a variavel de ambiente no Render.")

# ── NOVO: catalogo de planos (preco definido AQUI, no backend — nao confia no frontend) ──
PLANOS_CONFIG = {
    "kit_teste": {"title": "Kit Teste - InfluencIA", "price": 47.00, "plano_interno": "starter"},
    "kit_pro": {"title": "Kit Criador PRO - InfluencIA", "price": 97.00, "plano_interno": "pro"},
    "kit_agencia": {"title": "Kit Agencia - InfluencIA", "price": 197.00, "plano_interno": "business"},
}

# ── NOVO: Meta Conversions API (evento de Purchase server-to-server) ──
# META_PIXEL_ID: mesmo ID usado no pixel do navegador (/config-publica).
# META_CAPI_ACCESS_TOKEN: gerado em Gerenciador de Eventos > Pixel > Configuracoes > API de Conversoes > Gerar token de acesso.
# Sem essas duas variaveis configuradas, o envio e simplesmente pulado (nao quebra o webhook).
META_PIXEL_ID = os.getenv("META_PIXEL_ID", "")
META_CAPI_ACCESS_TOKEN = os.getenv("META_CAPI_ACCESS_TOKEN", "")

def enviar_purchase_meta(db_user, valor, payment_id, request: Request = None):
    """Envia o evento Purchase para o Meta via Conversions API (server-side),
    para que campanhas de Conversao no Ads Manager tenham um sinal real de venda."""
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


class User(BaseModel):
    username: str
    email: str
    password: str

class LoginUser(BaseModel):
    username: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token invalido")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

@app.post("/register")
def register(user: User, db: Session = Depends(get_db)):
    existing = db.query(DBUser).filter(DBUser.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ja existe")

    existing_email = db.query(DBUser).filter(DBUser.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Este e-mail ja esta cadastrado")

    new_user = DBUser(
        username=user.username,
        email=user.email,
        password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "Usuario criado com sucesso"}

@app.post("/login")
def login(user: LoginUser, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Usuario nao existe")
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Senha incorreta")
    token = create_token({"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}


# ── NOVO: Esqueci minha senha - envia email com link de redefinicao ──
class EsqueciSenhaRequest(BaseModel):
    email: str

@app.post("/esqueci-senha")
def esqueci_senha(req: EsqueciSenhaRequest, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.email == req.email).first()
    # Sempre retorna sucesso (mesmo se o email nao existir) para nao revelar quais emails estao cadastrados
    if not db_user:
        return {"msg": "Se esse e-mail estiver correto e cadastrado, voce vai receber o link em alguns instantes. Confira tambem a caixa de spam."}

    reset_token = jwt.encode(
        {"sub": db_user.username, "purpose": "reset_password", "exp": datetime.utcnow() + timedelta(minutes=30)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    reset_link = f"{APP_URL}/app?reset_token={reset_token}"

    if not BREVO_API_KEY:
        print(f"[AVISO] BREVO_API_KEY nao configurada. Link de reset (debug): {reset_link}")
        return {"msg": "Se esse e-mail estiver correto e cadastrado, voce vai receber o link em alguns instantes. Confira tambem a caixa de spam."}

    try:
        corpo_html = f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
                <h2 style="color:#a78bfa;">InfluencIA</h2>
                <p>Voce solicitou a redefinicao da sua senha.</p>
                <p><a href="{reset_link}" style="background:#ec4899;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block;">Redefinir senha</a></p>
                <p style="color:#888;font-size:12px;">Este link expira em 30 minutos. Se voce nao solicitou isso, ignore este email.</p>
            </div>
        """
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json", "accept": "application/json"},
            json={
                "sender": {"name": "InfluencIA", "email": BREVO_SENDER_EMAIL},
                "to": [{"email": db_user.email}],
                "subject": "Redefinir senha - InfluencIA",
                "htmlContent": corpo_html
            },
            timeout=15
        )
        if resp.status_code not in (200, 201):
            print(f"[ERRO] Brevo respondeu {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar email via Brevo: {e}")

    return {"msg": "Se o email existir, um link de redefinicao foi enviado."}


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str

@app.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(req.token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "reset_password":
            raise HTTPException(status_code=400, detail="Token invalido")
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=400, detail="Link invalido ou expirado")

    db_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    db_user.password = hash_password(req.nova_senha)
    db.commit()
    return {"msg": "Senha redefinida com sucesso!"}


# ── NOVO: Login com Google ──
class GoogleLoginRequest(BaseModel):
    credential: str

@app.post("/login-google")
def login_google(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Login com Google nao configurado no servidor")

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        idinfo = google_id_token.verify_oauth2_token(
            req.credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token do Google invalido: {str(e)}")

    email = idinfo.get("email")
    nome = idinfo.get("name") or email.split("@")[0]

    if not email:
        raise HTTPException(status_code=400, detail="Nao foi possivel obter o email da conta Google")

    db_user = db.query(DBUser).filter(DBUser.email == email).first()
    if not db_user:
        # Cria conta automaticamente na primeira vez que loga com Google
        username_base = nome
        username_final = username_base
        contador = 1
        while db.query(DBUser).filter(DBUser.username == username_final).first():
            contador += 1
            username_final = f"{username_base}{contador}"

        db_user = DBUser(
            username=username_final,
            email=email,
            password=hash_password(os.urandom(16).hex())  # senha aleatoria, usuario so entra via Google
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    token = create_token({"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}

# ── NOVO: endpoint que faltava — resolve o problema do e-mail nao aparecer no topo ──
@app.get("/me")
def me(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.username == user).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "plano": db_user.plano
    }

@app.get("/painel")
def painel(user: str = Depends(get_current_user)):
    return {"msg": f"Bem vindo, {user}!"}

@app.get("/creditos")
def get_creditos(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.username == user).first()
    mes_atual = datetime.now().strftime("%Y-%m")
    if db_user.mes_referencia != mes_atual:
        db_user.scripts_usados = 0
        db_user.imagens_usadas = 0
        db_user.imagens_pro_usadas = 0
        db_user.mes_referencia = mes_atual
        db.commit()
    limites = {
        "starter": {"scripts": 50, "imagens": 20, "imagens_pro": 5},
        "free": {"scripts": 3, "imagens": 2, "imagens_pro": 0},
        "pro": {"scripts": 150, "imagens": 60, "imagens_pro": 25},
        "business": {"scripts": 400, "imagens": 200, "imagens_pro": 60}
    }
    plano = db_user.plano or "free"
    limite = limites.get(plano, limites["free"])
    return {
        "plano": plano,
        "scripts": {"usados": db_user.scripts_usados, "limite": limite["scripts"]},
        "imagens": {"usados": db_user.imagens_usadas, "limite": limite["imagens"]},
        "imagens_pro": {"usados": db_user.imagens_pro_usadas, "limite": limite["imagens_pro"]}
    }

app.include_router(script_router)


# ── NOVO: cria uma preferencia de pagamento DINAMICA e AUTENTICADA ──
# Isso substitui os links estaticos (mpago.la/xxxx) do frontend.
# Agora cada pagamento nasce ja vinculado ao user_id de quem esta logado.
@app.post("/criar-pagamento/{plano_id}")
def criar_pagamento(
    plano_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if plano_id not in PLANOS_CONFIG:
        raise HTTPException(status_code=400, detail="Plano invalido")

    if not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MP_ACCESS_TOKEN nao configurado no servidor")

    db_user = db.query(DBUser).filter(DBUser.username == user).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    plano_info = PLANOS_CONFIG[plano_id]

    # external_reference usa EMAIL (estavel entre reinicios do DB efemero).
    # Formato: {email}#{plano_id}  ex: djraffa4@gmail.com#kit_pro
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


# ── CORRIGIDO: webhook agora identifica o usuario por ID (via external_reference)
# como fonte primaria de verdade, com fallback por e-mail apenas se necessario. ──
@app.post("/webhook")
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
        event_type = payload.get("action") or payload.get("type")

        if event_type in ["payment.created", "payment.updated", "payment"]:
            data = payload.get("data", {})
            payment_id = data.get("id") or payload.get("id")

            print(f"\n[MERCADO PAGO] Notificacao recebida! Consultando ID: {payment_id}...")

            headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
            url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
            mp_response = requests.get(url, headers=headers)

            if mp_response.status_code == 200:
                payment_data = mp_response.json()
                status = payment_data.get("status")

                if status == "approved":
                    external_ref = (payment_data.get("external_reference") or "").strip()
                    payer_email = payment_data.get("payer", {}).get("email")

                    db_user = None
                    plano_id_extraido = None

                    # 1) Novo formato: {email}#{plano_id} (estavel entre reinicios)
                    if "#" in external_ref and "@" in external_ref:
                        email_ref, _, plano_id_extraido = external_ref.partition("#")
                        db_user = db.query(DBUser).filter(DBUser.email == email_ref).first()

                    # 2) Formato user_id: user_{id}_{plano_id} (legado, instavel)
                    if not db_user and external_ref.startswith("user_"):
                        partes = external_ref.split("_")
                        if len(partes) >= 3:
                            try:
                                user_id = int(partes[1])
                                plano_id_extraido = "_".join(partes[2:])
                                db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
                                if db_user:
                                    print(f"[AVISO] Webhook usou user_id legado ({external_ref}). Considere recriar o pagamento.")
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
        return {"status": "error", "message": str(e)}


# --- ATIVACAO MANUAL DE PLANO (admin) --------------------------------------
class AtivarPlanoRequest(BaseModel):
    email_ou_username: str
    plano: str
    admin_key: str

@app.post("/admin/ativar-plano")
def ativar_plano(req: AtivarPlanoRequest, db: Session = Depends(get_db)):
    if req.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Nao autorizado")
    db_user = db.query(DBUser).filter(
        (DBUser.email == req.email_ou_username) |
        (DBUser.username == req.email_ou_username)
    ).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    planos_validos = ["free", "starter", "pro", "business"]
    if req.plano not in planos_validos:
        raise HTTPException(status_code=400, detail=f"Plano invalido")
    db_user.plano = req.plano
    db.commit()
    return {"msg": f"Plano {req.plano} ativado para {db_user.username}"}


# --- ATUALIZAR EMAIL (admin) ------------------------------------------------
class AtualizarEmailRequest(BaseModel):
    username: str
    email: str
    admin_key: str

@app.post("/admin/atualizar-email")
def atualizar_email(req: AtualizarEmailRequest, db: Session = Depends(get_db)):
    if req.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Nao autorizado")
    db_user = db.query(DBUser).filter(DBUser.username == req.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    existing = db.query(DBUser).filter(DBUser.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")
    db_user.email = req.email
    db.commit()
    return {"msg": f"Email atualizado para {req.email} no usuario {req.username}"}

@app.get("/admin/listar-usuarios")
def listar_usuarios(admin_key: str, db: Session = Depends(get_db)):
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Nao autorizado")
    users = db.query(DBUser).all()
    return [{"id": u.id, "username": u.username, "email": u.email, "plano": u.plano} for u in users]
