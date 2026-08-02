from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    password = Column(String)
    plano = Column(String, default="free")
    scripts_usados = Column(Integer, default=0)
    imagens_usadas = Column(Integer, default=0)
    imagens_pro_usadas = Column(Integer, default=0)
    mes_referencia = Column(String, default="")

class Historico(Base):
    __tablename__ = "historico"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    tipo = Column(String)
    data_hora = Column(DateTime, default=datetime.utcnow)


class VisitaDemo(Base):
    __tablename__ = "visita_demo"
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, index=True)
    tipo = Column(String)
    data_hora = Column(DateTime, default=datetime.utcnow)
