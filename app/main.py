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
import os`nimport requests
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

SECRET_KEY = "minha-chave-super-secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = HTTPBearer()

# Substitua pelo seu Access Token de Producao real do Mercado Pago
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

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
                    payer_email = payment_data.get("payer", {}).get("email")

                    if payer_email:
                        db_user = db.query(DBUser).filter(DBUser.email == payer_email).first()

                        if db_user:
                            external_ref = payment_data.get("external_reference", "").lower().strip()
                            planos = {"kit_teste": "starter", "kit_pro": "pro", "kit_agencia": "business"}
                            db_user.plano = planos.get(external_ref, "pro")
                            db.commit()
                            print(f"[SUCESSO] Plano PRO liberado para o e-mail: {payer_email}!")
                        else:
                            print(f"[AVISO] Pagamento aprovado, mas o e-mail {payer_email} nao foi encontrado no banco de dados.")
                    else:
                        print("[AVISO] E-mail do comprador nao encontrado nos dados do pagamento.")
                else:
                    print(f"[AGUARDANDO] O pagamento {payment_id} esta com status: {status}")
            else:
                print(f"[ERRO] Falha ao consultar o Mercado Pago: {mp_response.text}")

        return {"status": "ok"}

    except Exception as e:
        print(f"[ERRO GRAVE] Falha ao processar webhook: {str(e)}")
        return {"status": "error", "message": str(e)}
