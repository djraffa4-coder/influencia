conteudo = open("app/main.py", "r", encoding="utf-8").read()

novo_endpoint = '''
@app.get("/creditos")
def get_creditos(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime
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
'''

if '/creditos' not in conteudo:
    conteudo = conteudo.replace(
        "app.include_router(script_router)",
        novo_endpoint + "\napp.include_router(script_router)"
    )
    print("endpoint creditos adicionado!")
else:
    print("creditos ja existe")

with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(conteudo)
print("feito!")