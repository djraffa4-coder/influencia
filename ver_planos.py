html = open("static/index.html", encoding="utf-8", errors="ignore").read()

# Pega a pagina de planos/upgrade
for termo in ["page-planos", "page-upgrade", "page-perfil", "upgrade-box", "plano"]:
    idx = html.find(f'id="{termo}"')
    if idx > 0:
        print(f"=== ENCONTRADO: {termo} ===")
        print(html[idx:idx+2000])
        print()
        break
