from sqlalchemy import Column, Integer, String
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