import os, re

EXCLUDE = {'.git', '__pycache__', 'venv', '.venv', 'node_modules', '.idea', '.vscode'}

def tree(path, prefix=""):
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return
    entries = [e for e in entries if e not in EXCLUDE]
    for i, entry in enumerate(entries):
        full = os.path.join(path, entry)
        connector = "+-- " if i == len(entries)-1 else "+-- "
        if os.path.isdir(full):
            print(prefix + connector + entry + "/")
            tree(full, prefix + ("    " if i == len(entries)-1 else "|   "))
        else:
            print(prefix + connector + f"{entry} ({os.path.getsize(full)} bytes)")

print("=== ESTRUTURA DO PROJETO ===")
tree(".")

print("\n=== ROTAS E FUNCOES PYTHON ===")
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in EXCLUDE]
    for f in files:
        if f.endswith(".py") and f not in ("diagnostico.py", "verificar.py"):
            fpath = os.path.join(root, f)
            print(f"\n--- {fpath} ---")
            with open(fpath, encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh):
                    s = line.strip()
                    if s.startswith(("def ", "class ", "@app.", "@router.")):
                        print(f"  L{i+1}: {s}")

print("\n=== requirements.txt ===")
print(open("requirements.txt", encoding="utf-8").read() if os.path.exists("requirements.txt") else "nao encontrado")

print("\n=== static/index.html (resumo) ===")
idx = "static/index.html"
if os.path.exists(idx):
    html = open(idx, encoding="utf-8").read()
    print("tamanho:", len(html), "caracteres")
    funcs = re.findall(r'function\s+(\w+)\s*\(', html)
    print("total de funcoes JS:", len(funcs))
    print(funcs)
    print("chaves { abertas:", html.count("{"), " } fechadas:", html.count("}"))
else:
    print("nao encontrado")
