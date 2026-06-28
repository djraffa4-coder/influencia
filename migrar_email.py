import sqlite3

conn = sqlite3.connect("saas.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(users)")
colunas = [c[1] for c in cursor.fetchall()]

if "email" in colunas:
    print("A coluna email ja existe. Nada a fazer.")
else:
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    conn.commit()
    print("OK! Coluna email adicionada na tabela users.")

conn.close()
