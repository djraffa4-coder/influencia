"""Chamadas as APIs de IA e armazenamento das imagens geradas."""
import base64
import time
import uuid

import requests
from fastapi import HTTPException

from app.config import GEMINI_KEY, TIMEOUT_IA
from app.models import Imagem

URL_GEMINI_TEXTO = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
URL_GEMINI_IMAGEM = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"


def _post_gemini(url, payload, timeout):
    try:
        r = requests.post(url, params={"key": GEMINI_KEY}, json=payload, timeout=timeout)
        return r.json()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="A IA demorou demais para responder, tente novamente em instantes")
    except Exception as e:
        print(f"[ERRO] Falha ao chamar Gemini: {e}")
        raise HTTPException(status_code=502, detail="Erro ao falar com a IA, tente novamente")


def _partes(data):
    candidatos = data.get("candidates") or [{}]
    return (candidatos[0].get("content") or {}).get("parts") or []


def gemini_texto(parts, timeout=TIMEOUT_IA):
    """Retorna o texto gerado, ou None se a IA nao devolveu nada."""
    data = _post_gemini(URL_GEMINI_TEXTO, {"contents": [{"parts": parts}]}, timeout)
    for part in _partes(data):
        if part.get("text"):
            return part["text"]
    print(f"[ERRO] Gemini texto sem resposta: {str(data)[:300]}")
    return None


def gemini_imagem(parts, timeout=TIMEOUT_IA):
    """Retorna os bytes da imagem gerada, ou None. Tenta de novo uma vez se o modelo estiver sobrecarregado."""
    payload = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}}
    for tentativa in range(2):
        data = _post_gemini(URL_GEMINI_IMAGEM, payload, timeout)
        for part in _partes(data):
            if "inlineData" in part:
                return base64.b64decode(part["inlineData"]["data"])
        if tentativa == 0 and "UNAVAILABLE" in str(data):
            time.sleep(2)
            continue
        print(f"[ERRO] Gemini imagem sem resposta: {str(data)[:300]}")
        return None


def salvar_imagem(db, dados: bytes, username=None, mime="image/jpeg"):
    """Grava a imagem no banco e devolve a URL publica (servida por /imagens/{id}.jpg)."""
    img_id = str(uuid.uuid4())
    db.add(Imagem(id=img_id, username=username, dados=dados, mime=mime))
    return f"/imagens/{img_id}.jpg"
