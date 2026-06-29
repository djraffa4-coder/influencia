import re

# ── 1. Redireciona / para /app ──────────────────────────────
main = open("app/main.py", encoding="utf-8").read()
if 'def raiz' not in main:
    main = main.replace(
        '@app.get("/app")',
        '@app.get("/")\ndef raiz():\n    from fastapi.responses import RedirectResponse\n    return RedirectResponse(url="/app")\n\n@app.get("/app")'
    )
    open("app/main.py", "w", encoding="utf-8").write(main)
    print("OK: redirecionamento / -> /app")
else:
    print("OK: redirecionamento ja existe")

# ── 2. Corrige frontend: botão upgrade + nome do usuario ────
html = open("static/index.html", encoding="utf-8").read()
original = html

# Botão upgrade abre modal de planos
OLD_UPG = '<button class="upgrade-btn">&#128640; Ver planos</button>'
NEW_UPG = '<button class="upgrade-btn" onclick="abrirModalPlanos()">&#128640; Ver planos</button>'
if OLD_UPG in html:
    html = html.replace(OLD_UPG, NEW_UPG)
    print("OK: botao upgrade corrigido")

# Também corrige o botão que pode estar com onclick vazio
html = re.sub(
    r'<button class="upgrade-btn"[^>]*>&#128640; Ver planos</button>',
    '<button class="upgrade-btn" onclick="abrirModalPlanos()">&#128640; Ver planos</button>',
    html
)

# Corrige o nome exibido: usa username em vez de email generico
# No topbar, o email hardcodado
OLD_EMAIL = '<div style="font-size:12px;color:#888;">usuario@email.com</div>'
NEW_EMAIL = '<div style="font-size:12px;color:#888;" id="user-email-top"></div>'
if OLD_EMAIL in html:
    html = html.replace(OLD_EMAIL, NEW_EMAIL)
    print("OK: email do topbar corrigido")

# Modal de planos + JS corrigido
MODAL_PLANOS = """
<!-- Modal Planos -->
<div id="modal-planos" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:9000;align-items:center;justify-content:center;overflow-y:auto;">
  <div style="background:#13131f;border:1px solid #2a2a4a;border-radius:24px;padding:40px;max-width:860px;width:95%;margin:40px auto;position:relative;">
    <button onclick="fecharModalPlanos()" style="position:absolute;top:20px;right:20px;background:none;border:none;color:#888;font-size:24px;cursor:pointer;">&#10005;</button>
    <h2 style="font-size:28px;font-weight:700;text-align:center;margin-bottom:8px;">Escolha seu <span style="color:#ec4899;">Plano</span></h2>
    <p style="text-align:center;color:#888;margin-bottom:32px;">Cancele quando quiser. Acesso imediato após pagamento.</p>
    <div style="display:flex;gap:20px;flex-wrap:wrap;justify-content:center;">
      <div style="flex:1;min-width:220px;background:rgba(30,30,45,0.6);border:1px solid rgba(255,255,255,0.05);border-radius:20px;padding:28px;text-align:center;">
        <h3 style="color:#a78bfa;margin-bottom:8px;">Kit Teste</h3>
        <div style="font-size:36px;font-weight:700;margin:12px 0;">R$ 47</div>
        <p style="color:#888;font-size:13px;margin-bottom:20px;">50 Scripts + 20 Imagens</p>
        <ul style="list-style:none;text-align:left;font-size:13px;color:#aaa;margin-bottom:24px;padding:0;">
          <li style="padding:4px 0;">&#10003; 50 scripts por mes</li>
          <li style="padding:4px 0;">&#10003; 20 imagens por mes</li>
          <li style="padding:4px 0;">&#10003; 5 Influencer Pro</li>
          <li style="padding:4px 0;">&#10003; Suporte basico</li>
        </ul>
        <button onclick="window.open('https://mpago.la/1tqcfBb','_blank')" style="width:100%;padding:12px;background:linear-gradient(135deg,#a78bfa,#ec4899);border:none;border-radius:10px;color:#fff;font-weight:700;cursor:pointer;font-size:14px;">ASSINAR AGORA</button>
      </div>
      <div style="flex:1;min-width:220px;background:rgba(30,30,45,0.6);border:2px solid #ec4899;border-radius:20px;padding:28px;text-align:center;position:relative;">
        <div style="position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:#ec4899;color:#fff;font-size:11px;font-weight:700;padding:4px 16px;border-radius:20px;letter-spacing:1px;">MAIS VENDIDO</div>
        <h3 style="color:#ec4899;margin-bottom:8px;">Kit Criador PRO</h3>
        <div style="font-size:36px;font-weight:700;margin:12px 0;">R$ 97</div>
        <p style="color:#888;font-size:13px;margin-bottom:20px;">150 Scripts + 60 Imagens + VIP</p>
        <ul style="list-style:none;text-align:left;font-size:13px;color:#aaa;margin-bottom:24px;padding:0;">
          <li style="padding:4px 0;">&#10003; 150 scripts por mes</li>
          <li style="padding:4px 0;">&#10003; 60 imagens por mes</li>
          <li style="padding:4px 0;">&#10003; 25 Influencer Pro</li>
          <li style="padding:4px 0;">&#10003; Banco de Influencers</li>
          <li style="padding:4px 0;">&#10003; Acervo VIP</li>
          <li style="padding:4px 0;">&#10003; Suporte prioritario</li>
        </ul>
        <button onclick="window.open('https://mpago.la/2q4sz9E','_blank')" style="width:100%;padding:12px;background:linear-gradient(135deg,#a78bfa,#ec4899);border:none;border-radius:10px;color:#fff;font-weight:700;cursor:pointer;font-size:14px;">RECOMENDADO</button>
      </div>
      <div style="flex:1;min-width:220px;background:rgba(30,30,45,0.6);border:1px solid rgba(255,255,255,0.05);border-radius:20px;padding:28px;text-align:center;">
        <h3 style="color:#fff;margin-bottom:8px;">Kit Agencia</h3>
        <div style="font-size:36px;font-weight:700;margin:12px 0;">R$ 197</div>
        <p style="color:#888;font-size:13px;margin-bottom:20px;">400 Scripts + 200 Imagens</p>
        <ul style="list-style:none;text-align:left;font-size:13px;color:#aaa;margin-bottom:24px;padding:0;">
          <li style="padding:4px 0;">&#10003; 400 scripts por mes</li>
          <li style="padding:4px 0;">&#10003; 200 imagens por mes</li>
          <li style="padding:4px 0;">&#10003; 60 Influencer Pro</li>
          <li style="padding:4px 0;">&#10003; Tudo do PRO</li>
          <li style="padding:4px 0;">&#10003; Suporte 24h</li>
          <li style="padding:4px 0;">&#10003; Multi-usuario</li>
        </ul>
        <button onclick="window.open('https://mpago.la/1i7fnYj','_blank')" style="width:100%;padding:12px;background:linear-gradient(135deg,#a78bfa,#ec4899);border:none;border-radius:10px;color:#fff;font-weight:700;cursor:pointer;font-size:14px;">ASSINAR AGORA</button>
      </div>
    </div>
    <p style="text-align:center;color:#555;font-size:12px;margin-top:24px;">Apos o pagamento, seu plano e ativado automaticamente pelo e-mail cadastrado.</p>
  </div>
</div>
"""

JS_MODAL = """
<script>
// ── Modal de planos ─────────────────────────────────────────
function abrirModalPlanos(){
    document.getElementById("modal-planos").style.display="flex";
    document.body.style.overflow="hidden";
}
function fecharModalPlanos(){
    document.getElementById("modal-planos").style.display="none";
    document.body.style.overflow="";
}
document.addEventListener("keydown",function(e){
    if(e.key==="Escape") fecharModalPlanos();
});

// ── Mostra nome real do usuario (nao email) ─────────────────
var _showAppOrig = typeof showApp === "function" ? showApp : null;
function showApp(username){
    document.getElementById("login-screen").style.display="none";
    document.getElementById("app-screen").style.display="flex";
    // Exibe apenas a parte antes do @ se for email
    var nomeExibido = username.includes("@") ? username.split("@")[0] : username;
    nomeExibido = nomeExibido.charAt(0).toUpperCase() + nomeExibido.slice(1);
    document.getElementById("user-name-top").textContent = nomeExibido;
    document.getElementById("user-avatar").textContent = nomeExibido[0].toUpperCase();
    var emailEl = document.getElementById("user-email-top");
    if(emailEl) emailEl.textContent = username;
    carregarCreditos();
    showPage("dashboard", document.getElementById("menu-dashboard"));
}

// ── Botoes Assinar na dashboard tambem abrem o modal ────────
document.addEventListener("DOMContentLoaded", function(){
    // Botoes .btn-assinar que nao tem onclick definido
    document.querySelectorAll(".btn-assinar").forEach(function(btn){
        if(!btn.getAttribute("onclick")){
            btn.addEventListener("click", abrirModalPlanos);
        }
    });
    // Botao upgrade-btn na sidebar
    document.querySelectorAll(".upgrade-btn").forEach(function(btn){
        btn.onclick = abrirModalPlanos;
    });
});
</script>
"""

# Insere modal antes de </body>
if "modal-planos" not in html:
    html = html.replace("</body>", MODAL_PLANOS + JS_MODAL + "\n</body>")
    print("OK: modal de planos + JS injetados")
else:
    print("modal ja existe - atualizando JS apenas")
    if "abrirModalPlanos" not in html:
        html = html.replace("</body>", JS_MODAL + "\n</body>")

open("static/index.html", "w", encoding="utf-8").write(html)
if html != original:
    print("OK: index.html salvo")
else:
    print("AVISO: nenhuma alteracao detectada no HTML")
