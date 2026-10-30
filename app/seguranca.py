import hashlib
import hmac
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ADMIN_KEY

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = HTTPBearer()


def hash_password(password):
    return pwd_context.hash(password)

def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)

def create_token(data: dict, minutos: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=minutos)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
    username = payload.get("sub")
    # Token de redefinicao de senha nao serve para login
    if username is None or payload.get("purpose"):
        raise HTTPException(status_code=401, detail="Token invalido")
    return username

def impressao_senha(hash_senha: str):
    """Pedaco do hash da senha atual. Vai dentro do token de redefinicao:
    quando a senha muda, o link antigo deixa de valer (uso unico)."""
    return hashlib.sha256((hash_senha or "").encode()).hexdigest()[:16]


def obter_ip_visitante(request: Request):
    # O Render fica atras da Cloudflare, que sobrescreve CF-Connecting-IP / True-Client-IP
    # com o IP real — diferente do X-Forwarded-For, que o visitante consegue forjar.
    for cabecalho in ("cf-connecting-ip", "true-client-ip"):
        valor = request.headers.get(cabecalho)
        if valor:
            return valor.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


class LimitadorTentativas:
    """Limite simples em memoria: no maximo `maximo` falhas por chave dentro de `janela` segundos."""

    def __init__(self, maximo: int, janela: int):
        self.maximo = maximo
        self.janela = janela
        self.falhas = defaultdict(deque)

    def _limpar(self, chave):
        fila = self.falhas[chave]
        agora = time.time()
        while fila and agora - fila[0] > self.janela:
            fila.popleft()
        if not fila:
            del self.falhas[chave]
        return fila

    def bloqueado(self, chave):
        return len(self._limpar(chave)) >= self.maximo

    def registrar_falha(self, chave):
        self.falhas[chave].append(time.time())

    def limpar(self, chave):
        self.falhas.pop(chave, None)


limitador_login = LimitadorTentativas(maximo=10, janela=15 * 60)
limitador_admin = LimitadorTentativas(maximo=5, janela=15 * 60)


def checar_chave_admin(request: Request, chave: Optional[str]):
    ip = obter_ip_visitante(request)
    if limitador_admin.bloqueado(ip):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde 15 minutos.")
    if not hmac.compare_digest((chave or "").encode(), ADMIN_KEY.encode()):
        limitador_admin.registrar_falha(ip)
        raise HTTPException(status_code=403, detail="Nao autorizado")


def verificar_admin(
    request: Request,
    x_admin_key: Optional[str] = Header(None),
    admin_key: Optional[str] = None,
):
    """Aceita a chave pelo cabecalho X-Admin-Key (recomendado) ou ?admin_key= (compatibilidade)."""
    checar_chave_admin(request, x_admin_key or admin_key)
    return True
