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
def frontend():
    return FileResponse("static/index.html")

Base.metadata.create_all(bind=engine)

import sqlite3 as _sqlite3_migration

def _migrar_banco_automaticamente():
    try:
        conn = _sqlite3_migration.connect("saas.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        colunas = [c[1] for c in cursor.fetchall()]
        if "email" not in colunas:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            conn.commit()
            print("[MIGRACAO] Coluna email adicionada com sucesso.")
        else:
            print("[MIGRACAO] Coluna email ja existe, nada a fazer.")
        conn.close()
    except Exception as e:
        print(f"[MIGRACAO] Erro ao migrar banco: {e}")

_migrar_banco_automaticamente()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── CORRIGIDO: SECRET_KEY agora vem de variavel de ambiente ──
# No Render, va em Environment > Add Environment Variable:
#   JWT_SECRET_KEY = (gere uma string aleatoria longa, ex: openssl rand -hex 32)
# Localmente, se a variavel nao existir, usa um fallback SO PRA DEV.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-fallback-troque-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = HTTPBearer()

# Access Token de Producao do Mercado Pago (variavel de ambiente, ja existente)
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# ── NOVO: URL base da sua aplicacao no Render ──
# Ex: APP_URL = https://influencia.onrender.com
# Sem barra no final. Usado pros back_urls e notification_url do Mercado Pago.
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

# ── NOVO: catalogo de planos (preco definido AQUI, no backend — nao confia no frontend) ──
PLANOS_CONFIG = {
    "kit_teste": {"title": "Kit Teste - InfluencIA", "price": 47.00, "plano_interno": "starter"},
    "kit_pro": {"title": "Kit Criador PRO - InfluencIA", "price": 97.00, "plano_interno": "pro"},
    "kit_agencia": {"title": "Kit Agencia - InfluencIA", "price": 197.00, "plano_interno": "business"},
}


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

    # external_reference carrega o user_id de forma inequivoca.
    # Formato: user_<id>_<plano_id>  ex: user_2_kit_pro
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

                    # 1) Tentativa primaria: extrair user_id do external_reference
                    # Formato esperado: user_<id>_<plano_id>
                    if external_ref.startswith("user_"):
                        partes = external_ref.split("_")
                        if len(partes) >= 3:
                            try:
                                user_id = int(partes[1])
                                plano_id_extraido = "_".join(partes[2:])
                                db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
                            except ValueError:
                                db_user = None

                    # 2) Fallback: formato antigo (external_reference = "kit_pro" direto)
                    #    ou nao achou por ID -> tenta por e-mail
                    if not db_user and external_ref in PLANOS_CONFIG:
                        plano_id_extraido = external_ref

                    if not db_user and payer_email:
                        db_user = db.query(DBUser).filter(DBUser.email == payer_email).first()
                        if db_user:
                            print(f"[AVISO] Identificado por fallback de e-mail ({payer_email}), nao por external_reference. Verifique a integracao.")

                    if db_user:
                        plano_final = PLANOS_CONFIG.get(plano_id_extraido, {}).get("plano_interno", "pro")
                        db_user.plano = plano_final
                        db.commit()
                        print(f"[SUCESSO] Plano '{plano_final}' liberado para user_id={db_user.id} (username={db_user.username})")
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
    ADMIN_KEY = os.getenv("ADMIN_KEY", "influencia-admin-2024")
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