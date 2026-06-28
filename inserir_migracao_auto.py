conteudo = open("app/main.py", "r", encoding="utf-8").read()

bloco_migracao = """
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
"""

marcador = "Base.metadata.create_all(bind=engine)"

if "_migrar_banco_automaticamente" not in conteudo:
    conteudo = conteudo.replace(marcador, marcador + "\n" + bloco_migracao)
    open("app/main.py", "w", encoding="utf-8").write(conteudo)
    print("OK: migracao automatica inserida no main.py")
else:
    print("Ja existe, nada feito.")
