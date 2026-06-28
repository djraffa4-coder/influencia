html = open("static/index.html", encoding="utf-8", errors="ignore").read()

LINK_TESTE = "https://mpago.la/1tqcfBb"
LINK_PRO = "https://mpago.la/2q4sz9E"
LINK_AGENCIA = "https://mpago.la/1i7fnYj"

ANTIGO_1 = '<button class="btn-assinar">ASSINAR AGORA</button>'
NOVO_1 = f'<button class="btn-assinar" onclick="window.open(\'{LINK_TESTE}\',\'_blank\')">ASSINAR AGORA</button>'

ANTIGO_2 = '<button class="btn-assinar">RECOMENDADO</button>'
NOVO_2 = f'<button class="btn-assinar" onclick="window.open(\'{LINK_PRO}\',\'_blank\')">RECOMENDADO</button>'

ANTIGO_3 = '<button class="btn-assinar" style="background:#333;">EM BREVE</button>'
NOVO_3 = f'<button class="btn-assinar" onclick="window.open(\'{LINK_AGENCIA}\',\'_blank\')">ASSINAR AGORA</button>'

trocas = [(ANTIGO_1, NOVO_1, "Kit Teste"), (ANTIGO_2, NOVO_2, "Kit Criador PRO"), (ANTIGO_3, NOVO_3, "Kit Agencia")]
for antigo, novo, nome in trocas:
    if antigo in html:
        html = html.replace(antigo, novo, 1)
        print(f"OK: {nome} conectado!")
    else:
        print(f"AVISO: nao encontrei o botao de {nome}")

open("static/index.html", "w", encoding="utf-8").write(html)
