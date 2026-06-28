html = open("static/index.html", encoding="utf-8", errors="ignore").read()

# Pega a pagina perfil completa
idx = html.find('id="page-perfil"')
print(html[idx:idx+5000])
