import shutil, os
from datetime import datetime

print("Iniciando backup...")

# 1. Atualiza o backup_perfeito com o index.html atual
shutil.copy("static/index.html", "static/index_backup_perfeito.html")
print("OK: index_backup_perfeito.html atualizado!")

# 2. Cria zip completo do projeto
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
nome_zip = f"BACKUP_COMPLETO_{timestamp}"
pasta_destino = os.path.expanduser(f"~/Desktop/{nome_zip}")

EXCLUDE_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules", ".idea", ".vscode"}

base = os.path.abspath(".")
temp_dir = pasta_destino
os.makedirs(temp_dir, exist_ok=True)

total_arquivos = 0
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    rel = os.path.relpath(root, base)
    dest_root = os.path.join(temp_dir, rel) if rel != "." else temp_dir
    os.makedirs(dest_root, exist_ok=True)
    for f in files:
        if f == os.path.basename(__file__):
            continue
        try:
            shutil.copy(os.path.join(root, f), os.path.join(dest_root, f))
            total_arquivos += 1
        except Exception as e:
            print(f"Aviso: nao copiou {f}: {e}")

print(f"OK: {total_arquivos} arquivos copiados. Compactando...")
shutil.make_archive(pasta_destino, "zip", temp_dir)
shutil.rmtree(temp_dir)

tamanho_mb = os.path.getsize(pasta_destino + ".zip") / (1024*1024)
print(f"BACKUP CRIADO: {pasta_destino}.zip ({tamanho_mb:.1f} MB)")
