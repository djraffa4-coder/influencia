html = open("static/index.html", encoding="utf-8", errors="ignore").read()

ANTIGO = """if(d.url){document.getElementById("pro-img").src=d.url;document.getElementById("pro-download").href=d.url;document.getElementById("pro-result-empty").style.display="none";document.getElementById("pro-result").style.display="block";carregarCreditos();}"""

NOVO = """if(d.url){
    document.getElementById("pro-img").src=d.url;
    document.getElementById("pro-download").href=d.url;
    document.getElementById("pro-result-empty").style.display="none";
    document.getElementById("pro-result").style.display="block";
    carregarCreditos();
    var imagens=JSON.parse(localStorage.getItem("influencia_imagens")||"[]");
    imagens.unshift({url:d.url,produto:document.getElementById("pro-produto").value||"Influencer Pro",data:new Date().toLocaleDateString("pt-BR"),tipo:"pro"});
    localStorage.setItem("influencia_imagens",JSON.stringify(imagens));
}"""

if ANTIGO in html:
    html = html.replace(ANTIGO, NOVO)
    open("static/index.html", "w", encoding="utf-8").write(html)
    print("CORRIGIDO! Imagem Pro agora salva em Imagens Geradas.")
else:
    print("TRECHO NAO ENCONTRADO - me avisa!")
