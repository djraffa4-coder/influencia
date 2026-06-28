conteudo = open("app/routes/auth.py", "r", encoding="utf-8").read()

nova_chave = "AQ.Ab8RN6IOmrzsPqeBsFUJyW0T7plfQRkcGCLAot4uG_CW55O1aA"

import re

novo = re.sub(
    r'GEMINI_KEY = "[^"]*"',
    f'GEMINI_KEY = "{nova_chave}"',
    conteudo
)

with open("app/routes/auth.py", "w", encoding="utf-8") as f:
    f.write(novo)
print("Chave atualizada!")