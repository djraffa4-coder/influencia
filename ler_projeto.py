import os, json
from pathlib import Path

EXTS = {'.py','.js','.ts','.jsx','.tsx','.vue','.html','.css','.scss','.json','.env.example','.md','.txt','.sql','.yaml','.yml','.toml','.cfg','.ini'}
IGNORAR = {'node_modules','.git','__pycache__','.next','dist','build','venv','.venv','env','.env','coverage','.cache','uploads','static/media','migrations'}

def deve_ignorar(path):
    for p in path.parts:
        if p in IGNORAR or (p.startswith('.') and p not in {'.env.example'}):
            return True
    return False

raiz = Path('.')
saida = []
saida.append("=" * 60)
saida.append("PROJETO: " + raiz.resolve().name)
saida.append("=" * 60)
saida.append("\n### ESTRUTURA DE PASTAS ###\n")
for item in sorted(raiz.rglob('*')):
    if deve_ignorar(item.relative_to(raiz)):
        continue
    nivel = len(item.relative_to(raiz).parts) - 1
    prefixo = "  " * nivel + ("PASTA: " if item.is_dir() else "ARQ: ")
    saida.append(prefixo + item.name)

saida.append("\n\n### CONTEUDO DOS ARQUIVOS ###\n")
arquivos_lidos = 0
for arquivo in sorted(raiz.rglob('*')):
    if arquivo.is_dir():
        continue
    rel = arquivo.relative_to(raiz)
    if deve_ignorar(rel):
        continue
    if arquivo.suffix.lower() not in EXTS and arquivo.name not in {'.env.example','Dockerfile','docker-compose.yml'}:
        continue
    try:
        tamanho = arquivo.stat().st_size
        if tamanho > 150000:
            saida.append(f"\n--- {rel} [GRANDE: {tamanho//1024}KB] ---")
            continue
        conteudo = arquivo.read_text(encoding='utf-8', errors='replace')
        saida.append(f"\n--- {rel} ---")
        saida.append(conteudo)
        arquivos_lidos += 1
    except Exception as e:
        saida.append(f"\n--- {rel} [ERRO: {e}] ---")

saida.append(f"\n\n=== TOTAL: {arquivos_lidos} arquivos lidos ===")
texto = '\n'.join(saida)
with open('projeto_contexto.txt', 'w', encoding='utf-8') as f:
    f.write(texto)
print(f"OK - Arquivo gerado: projeto_contexto.txt")
print(f"Arquivos lidos: {arquivos_lidos}")
print(f"Tamanho: {len(texto)//1024} KB")
