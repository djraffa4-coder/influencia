# Reescreve o index.html completo e limpo
with open("static/index.html", "w", encoding="utf-8") as f:
    f.write(open("static/index_backup.html", encoding="utf-8").read())
print("backup restaurado!")