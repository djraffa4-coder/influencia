import sys
sys.path.insert(0, ".")
from app.database import SessionLocal
from app.models import User as DBUser

db = SessionLocal()

print("=" * 50)
print("LIBERAR PLANO - InfluencIA")
print("=" * 50)

usuarios = db.query(DBUser).all()
print("\nUsuarios cadastrados:")
for u in usuarios:
    print(f"  - {u.username} (plano atual: {u.plano or 'free'})")

print()
username = input("Digite o NOME DE USUARIO de quem pagou: ").strip()

usuario = db.query(DBUser).filter(DBUser.username == username).first()
if not usuario:
    print(f"ERRO: usuario '{username}' nao encontrado!")
else:
    print(f"\nPlano atual de {username}: {usuario.plano or 'free'}")
    print("Planos disponiveis: free, pro, business")
    novo_plano = input("Digite o NOVO PLANO (free/pro/business): ").strip().lower()
    if novo_plano not in ["free", "pro", "business"]:
        print("ERRO: plano invalido! Use free, pro ou business.")
    else:
        usuario.plano = novo_plano
        db.commit()
        print(f"\nSUCESSO! {username} agora esta no plano: {novo_plano}")

db.close()
