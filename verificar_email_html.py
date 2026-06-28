html = open("static/index.html", encoding="utf-8", errors="ignore").read()

print("=== VERIFICACAO ===")
print()

if "reg-email" in html:
    print("OK: o campo reg-email EXISTE no arquivo.")
else:
    print("PROBLEMA: o campo reg-email NAO foi encontrado no arquivo.")
    print("Isso significa que a edicao do formulario nao foi salva.")

print()
print("=== TRECHO ATUAL DO FORMULARIO DE CADASTRO ===")
idx = html.find("register-section")
if idx > 0:
    print(html[idx:idx+500])
else:
    print("Nao encontrei a secao register-section no arquivo.")
