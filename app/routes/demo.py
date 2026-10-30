from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import DEMO_LIMITE_DIARIO
from app.database import get_db
from app.ia import gemini_imagem, salvar_imagem
from app.models import VisitaDemo
from app.seguranca import obter_ip_visitante

router = APIRouter()


class EventoRequest(BaseModel):
    tipo: str

@router.post("/registrar-evento")
def registrar_evento(req: EventoRequest, request: Request, db: Session = Depends(get_db)):
    if req.tipo not in ["visita", "quiz_completo"]:
        raise HTTPException(status_code=400, detail="Tipo invalido")
    db.add(VisitaDemo(ip=obter_ip_visitante(request), tipo=req.tipo))
    db.commit()
    return {"ok": True}


class DemoRequest(BaseModel):
    produto: str

@router.post("/gerar-demo")
def gerar_demo(req: DemoRequest, request: Request, db: Session = Depends(get_db)):
    produto = (req.produto or "").strip()
    if len(produto) < 2:
        raise HTTPException(status_code=400, detail="Descreva o produto")
    if len(produto) > 200:
        raise HTTPException(status_code=400, detail="Descreva o produto em poucas palavras")

    ip = obter_ip_visitante(request)
    limite_tempo = datetime.utcnow() - timedelta(hours=24)
    demos_24h = db.query(VisitaDemo).filter(VisitaDemo.tipo == "demo_gerada", VisitaDemo.data_hora >= limite_tempo)
    if demos_24h.filter(VisitaDemo.ip == ip).first():
        raise HTTPException(status_code=429, detail="Voce ja gerou seu exemplo gratis hoje. Crie uma conta gratis para gerar mais!")
    if demos_24h.count() >= DEMO_LIMITE_DIARIO:
        raise HTTPException(status_code=429, detail="Os exemplos gratis de hoje acabaram. Crie uma conta gratis para gerar o seu!")

    prompt_texto = f"Generate a photorealistic portrait of a beautiful woman, 26 year old Brazilian Japanese woman from Rio de Janeiro, long straight black hair, TikTok influencer style. She is holding and showing a {produto} to the camera, product clearly visible in her hand. Clean modern background, professional photography, no text, no watermarks, photorealistic, 8k quality."
    img_data = gemini_imagem([{"text": prompt_texto}], timeout=25)
    if not img_data:
        raise HTTPException(status_code=502, detail="Nao foi possivel gerar o exemplo agora, tente novamente")

    url = salvar_imagem(db, img_data)
    db.add(VisitaDemo(ip=ip, tipo="demo_gerada"))
    db.commit()
    return {"url": url}
