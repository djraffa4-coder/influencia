conteudo = open("app/routes/auth.py", "r", encoding="utf-8").read()

old = '''    prompt = f"Voce e {perfil['nome']}, uma influenciadora digital brasileira do TikTok. Crie um script de venda de 15 a 20 segundos para: {req.produto}. Nicho: {req.nicho}. Tom: {req.tom}. Comece com gancho forte, mostre beneficios rapidamente e termine com call to action urgente. Apenas o script, sem titulos ou numeracao."'''

new = '''    prompt = f"""Voce e {perfil['nome']}, um influencer digital brasileiro do TikTok.

Crie um script de venda de EXATAMENTE 10 segundos falados para o produto: {req.produto}.
Nicho: {req.nicho}. Tom: {req.tom}.

REGRAS OBRIGATORIAS:
- Maximo 3 frases curtas e diretas
- Comece com gancho impactante (surpreenda nos primeiros 2 segundos)
- Mencione 1 beneficio especifico e real do produto
- Termine com CTA urgente e direto (ex: "Link na bio!", "Corre la!", "Garante ja!")
- Linguagem natural de TikTok brasileiro
- SEM asteriscos, SEM parenteses, SEM indicacoes de cena, SEM numeracao
- Apenas o texto que sera falado, nada mais

Exemplo de formato correto para um perfume:
Gente, esse perfume mudou minha vida! Dura o dia todo e todo mundo pergunta qual e. Corre no link da bio antes que esgote!

Agora crie para: {req.produto}"""'''

if old in conteudo:
    conteudo = conteudo.replace(old, new)
    print("prompt atualizado!")
else:
    print("TRECHO NAO ENCONTRADO")

with open("app/routes/auth.py", "w", encoding="utf-8") as f:
    f.write(conteudo)
print("feito!")