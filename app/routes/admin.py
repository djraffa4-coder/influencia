from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User as DBUser, VisitaDemo
from app.seguranca import checar_chave_admin, obter_ip_visitante, verificar_admin

# A chave de admin vai de preferencia no cabecalho X-Admin-Key.
# Por compatibilidade, ainda e aceita em ?admin_key= (GET) ou no campo admin_key do corpo (POST).
router = APIRouter(prefix="/admin")

PLANOS_VALIDOS = ["free", "starter", "pro", "business"]


class AtivarPlanoRequest(BaseModel):
    email_ou_username: str
    plano: str
    admin_key: Optional[str] = None

@router.post("/ativar-plano")
def ativar_plano(req: AtivarPlanoRequest, request: Request, db: Session = Depends(get_db)):
    checar_chave_admin(request, request.headers.get("x-admin-key") or req.admin_key)
    db_user = db.query(DBUser).filter(
        (DBUser.email == req.email_ou_username) |
        (DBUser.username == req.email_ou_username)
    ).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if req.plano not in PLANOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Plano invalido")
    db_user.plano = req.plano
    db.commit()
    return {"msg": f"Plano {req.plano} ativado para {db_user.username}"}


class AtualizarEmailRequest(BaseModel):
    username: str
    email: str
    admin_key: Optional[str] = None

@router.post("/atualizar-email")
def atualizar_email(req: AtualizarEmailRequest, request: Request, db: Session = Depends(get_db)):
    checar_chave_admin(request, request.headers.get("x-admin-key") or req.admin_key)
    db_user = db.query(DBUser).filter(DBUser.username == req.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if db.query(DBUser).filter(DBUser.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email ja cadastrado")
    db_user.email = req.email
    db.commit()
    return {"msg": f"Email atualizado para {req.email} no usuario {req.username}"}


@router.get("/listar-usuarios", dependencies=[Depends(verificar_admin)])
def listar_usuarios(db: Session = Depends(get_db)):
    users = db.query(DBUser).all()
    return [{"id": u.id, "username": u.username, "email": u.email, "plano": u.plano} for u in users]


@router.post("/resetar-demo", dependencies=[Depends(verificar_admin)])
def resetar_demo(request: Request, ip: str = None, db: Session = Depends(get_db)):
    alvo_ip = ip if ip else obter_ip_visitante(request)
    apagados = db.query(VisitaDemo).filter(VisitaDemo.ip == alvo_ip, VisitaDemo.tipo == "demo_gerada").delete()
    db.commit()
    return {"ip": alvo_ip, "registros_removidos": apagados}


@router.get("/estatisticas-demo", dependencies=[Depends(verificar_admin)])
def estatisticas_demo(db: Session = Depends(get_db)):
    total_visitas = db.query(VisitaDemo).filter(VisitaDemo.tipo == "visita").count()
    total_quiz = db.query(VisitaDemo).filter(VisitaDemo.tipo == "quiz_completo").count()
    total_demos = db.query(VisitaDemo).filter(VisitaDemo.tipo == "demo_gerada").count()
    return {"visitas": total_visitas, "quiz_completo": total_quiz, "demos_geradas": total_demos}
