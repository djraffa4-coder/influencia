html = open("static/index.html", encoding="utf-8", errors="ignore").read()

ANTIGO_VAR = """var proUploadB64 = "";"""
NOVO_VAR = """var proUploadB64 = "";
var planoAtual = "free";"""

ANTIGO_CRED = """var plano=d.plano.charAt(0).toUpperCase()+d.plano.slice(1);"""
NOVO_CRED = """planoAtual=d.plano;
        var plano=d.plano.charAt(0).toUpperCase()+d.plano.slice(1);"""

ANTIGO_SHOWPAGE = """function showPage(page,el){
    document.querySelectorAll(".page").forEach(function(p){p.classList.remove("active");});
    document.querySelectorAll(".sidebar-item").forEach(function(i){i.classList.remove("active");});
    document.getElementById("page-"+page).classList.add("active");
    if(el)el.classList.add("active");
}"""

NOVO_SHOWPAGE = ANTIGO_SHOWPAGE + """
function acessarPagina(page,el){
    if((page==="banco-influenciadores"||page==="acervo-vip") && planoAtual==="free"){
        alert("Esse conteudo e exclusivo para planos Pro e Business. Faca upgrade para desbloquear!");
        return;
    }
    showPage(page,el);
}"""

ANTIGO_MENU1 = "showPage(\'banco-influenciadores\'"
NOVO_MENU1 = "acessarPagina(\'banco-influenciadores\'"

ANTIGO_MENU2 = "showPage(\'acervo-vip\'"
NOVO_MENU2 = "acessarPagina(\'acervo-vip\'"

trocas = [
    (ANTIGO_VAR, NOVO_VAR, "variavel planoAtual"),
    (ANTIGO_CRED, NOVO_CRED, "captura do plano"),
    (ANTIGO_SHOWPAGE, NOVO_SHOWPAGE, "funcao acessarPagina"),
    (ANTIGO_MENU1, NOVO_MENU1, "menu Banco Influencers"),
    (ANTIGO_MENU2, NOVO_MENU2, "menu Acervo VIP"),
]

for antigo, novo, nome in trocas:
    if antigo in html:
        html = html.replace(antigo, novo, 1)
        print("OK: " + nome)
    else:
        print("AVISO: nao encontrei " + nome)

open("static/index.html", "w", encoding="utf-8").write(html)
