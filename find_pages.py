import re
html = open("static/index.html", encoding="utf-8", errors="ignore").read()
ids = re.findall(r'id="(menu-[a-zA-Z0-9_-]+)"', html)
print("IDs de menu encontrados:")
for i in ids:
    print(" -", i)
print()
paginas = re.findall(r'id="page-([a-zA-Z0-9_-]+)"', html)
print("Paginas (page-) encontradas:")
for p in paginas:
    print(" -", p)
