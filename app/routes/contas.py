import os
import re
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import APP_URL, BREVO_API_KEY, BREVO_SENDER_EMAIL, GOOGLE_CLIENT_ID, LIMITES
from app.database import get_db
from app.models import User as DBUser
from app.seguranca import (
    create_token, decode_token, get_current_user, hash_password, verify_password,
    impressao_senha, limitador_login, obter_ip_visitante,
)

router = APIRouter()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SENHA_MINIMA = 6


class User(BaseModel):
    username: str
    email: str
    password: str

class LoginUser(BaseModel):
    username: str
    password: str


def validar_senha(senha: str):
    if len(senha or "") < SENHA_MINIMA:
        raise HTTPException(status_code=400, detail=f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres")


@router.post("/register")
def register(user: User, db: Session = Depends(get_db)):
    username = user.username.strip()
    email = user.email.strip().lower()
    if not 3 <= len(username) <= 40:
        raise HTTPException(status_code=400, detail="O usuario precisa ter entre 3 e 40 caracteres")
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Digite um e-mail valido")
    validar_senha(user.password)

    if db.query(DBUser).filter(DBUser.username == username).first():
        raise HTTPException(status_code=400, detail="Usuario ja existe")
    if db.query(DBUser).filter(DBUser.email == email).first():
        raise HTTPException(status_code=400, detail="Este e-mail ja esta cadastrado")

    db.add(DBUser(username=username, email=email, password=hash_password(user.password)))
    db.commit()
    return {"msg": "Usuario criado com sucesso"}


@router.post("/login")
def login(user: LoginUser, request: Request, db: Session = Depends(get_db)):
    chave = obter_ip_visitante(request)
    if limitador_login.bloqueado(chave):
        raise HTTPException(status_code=429, detail="Muitas tentativas de login. Aguarde 15 minutos e tente de novo.")

    db_user = db.query(DBUser).filter(DBUser.username == user.username.strip()).first()
    # Mesma mensagem para usuario inexistente e senha errada (nao revela quem tem conta)
    if not db_user or not verify_password(user.password, db_user.password):
        limitador_login.registrar_falha(chave)
        raise HTTPException(status_code=400, detail="Usuario ou senha incorretos")

    limitador_login.limpar(chave)
    return {"access_token": create_token({"sub": db_user.username}), "token_type": "bearer"}


# ── Esqueci minha senha - envia email com link de redefinicao ──
class EsqueciSenhaRequest(BaseModel):
    email: str

MSG_ESQUECI = "Se esse e-mail estiver correto e cadastrado, voce vai receber o link em alguns instantes. Confira tambem a caixa de spam."

@router.post("/esqueci-senha")
def esqueci_senha(req: EsqueciSenhaRequest, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.email == req.email.strip().lower()).first()
    if not db_user:
        db_user = db.query(DBUser).filter(DBUser.email == req.email.strip()).first()
    # Sempre retorna sucesso (mesmo se o email nao existir) para nao revelar quais emails estao cadastrados
    if not db_user:
        return {"msg": MSG_ESQUECI}

    reset_token = create_token(
        {"sub": db_user.username, "purpose": "reset_password", "pwd": impressao_senha(db_user.password)},
        minutos=30,
    )
    reset_link = f"{APP_URL}/app?reset_token={reset_token}"

    if not BREVO_API_KEY:
        print(f"[AVISO] BREVO_API_KEY nao configurada. Link de reset (debug): {reset_link}")
        return {"msg": MSG_ESQUECI}

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

    return {"msg": MSG_ESQUECI}


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str

@router.post("/redefinir-senha")
def redefinir_senha(req: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(req.token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Link invalido ou expirado")
    if payload.get("purpose") != "reset_password":
        raise HTTPException(status_code=400, detail="Link invalido ou expirado")

    db_user = db.query(DBUser).filter(DBUser.username == payload.get("sub")).first()
    # O link e de uso unico: depois que a senha muda, a impressao nao bate mais
    if not db_user or payload.get("pwd") != impressao_senha(db_user.password):
        raise HTTPException(status_code=400, detail="Link invalido ou ja utilizado. Peca um novo.")

    validar_senha(req.nova_senha)
    db_user.password = hash_password(req.nova_senha)
    db.commit()
    return {"msg": "Senha redefinida com sucesso!"}


# ── Login com Google ──
class GoogleLoginRequest(BaseModel):
    credential: str

@router.post("/login-google")
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
    if not email or not idinfo.get("email_verified", True):
        raise HTTPException(status_code=400, detail="Nao foi possivel obter o email da conta Google")
    nome = idinfo.get("name") or email.split("@")[0]

    db_user = db.query(DBUser).filter(DBUser.email == email).first()
    if not db_user:
        # Cria conta automaticamente na primeira vez que loga com Google
        username_final = nome
        contador = 1
        while db.query(DBUser).filter(DBUser.username == username_final).first():
            contador += 1
            username_final = f"{nome}{contador}"

        db_user = DBUser(
            username=username_final,
            email=email,
            password=hash_password(os.urandom(16).hex())  # senha aleatoria, usuario so entra via Google
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    return {"access_token": create_token({"sub": db_user.username}), "token_type": "bearer"}


@router.get("/me")
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

@router.get("/painel")
def painel(user: str = Depends(get_current_user)):
    return {"msg": f"Bem vindo, {user}!"}


def renovar_mes(db_user, db):
    """Zera os contadores quando vira o mes."""
    mes_atual = datetime.now().strftime("%Y-%m")
    if db_user.mes_referencia != mes_atual:
        db_user.scripts_usados = 0
        db_user.imagens_usadas = 0
        db_user.imagens_pro_usadas = 0
        db_user.videos_usados = 0
        db_user.mes_referencia = mes_atual
        db.commit()

@router.get("/creditos")
def get_creditos(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.username == user).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    renovar_mes(db_user, db)
    plano = db_user.plano or "free"
    limite = LIMITES.get(plano, LIMITES["free"])
    return {
        "plano": plano,
        "scripts": {"usados": db_user.scripts_usados or 0, "limite": limite["scripts"]},
        "imagens": {"usados": db_user.imagens_usadas or 0, "limite": limite["imagens"]},
        "imagens_pro": {"usados": db_user.imagens_pro_usadas or 0, "limite": limite["imagens_pro"]},
        "videos": {"usados": db_user.videos_usados or 0, "limite": limite["videos"]},
    }
