import re
html = open("static/index.html", encoding="utf-8", errors="ignore").read()

# Pega a pagina influencer-pro
start = html.find('id="page-influencer-pro"')
end = html.find('id="page-video"')
print("=== PAGE INFLUENCER-PRO ===")
print(html[start:end][:3000])

# Pega a funcao JS que gera imagem pro
js_start = html.find("function gerarImagemPro")
print("\n=== FUNCAO gerarImagemPro ===")
print(html[js_start:js_start+2000])

# Pega como imagens-geradas salva
js_start2 = html.find("imagens-geradas")
print("\n=== TRECHO imagens-geradas ===")
print(html[js_start2:js_start2+500])
