conteudo = open("app/main.py", encoding="utf-8").read()

redirecionamento = '''
from fastapi.responses import RedirectResponse

@app.get("/")
def raiz():
    return RedirectResponse(url="/app")
'''

if 'def raiz' not in conteudo:
    conteudo = conteudo.replace(
        '@app.get("/app")',
        redirecionamento + '\n@app.get("/app")'
    )
    open("app/main.py", "w", encoding="utf-8").write(conteudo)
    print("OK - redirecionamento adicionado")
else:
    print("ja existe")
