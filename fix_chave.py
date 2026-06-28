import re, os

caminho = "app/routes/auth.py"
c = open(caminho, encoding="utf-8").read()

# Remove todas as chaves hardcodadas
c = re.sub(r'GEMINI_KEY\s*=\s*"[^"]*"', 'GEMINI_KEY = os.getenv("GEMINI_KEY", "")', c)
c = re.sub(r"GEMINI_KEY\s*=\s*'[^']*'", 'GEMINI_KEY = os.getenv("GEMINI_KEY", "")', c)

# Garante import os no topo
if "import os" not in c[:200]:
    c = "import os\n" + c

open(caminho, "w", encoding="utf-8").write(c)
print("Chave removida!")
print("Verificando...")
for i, linha in enumerate(c.splitlines(), 1):
    if "AQ." in linha:
        print(f"  AINDA TEM: linha {i}: {linha[:60]}")
print("Pronto.")
