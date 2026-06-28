html = open("static/index.html", encoding="utf-8", errors="ignore").read()

ANTIGO_FORM = """<input type="text" id="reg-user" placeholder="Novo usuario">
            <input type="password" id="reg-pass" placeholder="Nova senha">"""

NOVO_FORM = """<input type="text" id="reg-user" placeholder="Novo usuario">
            <input type="email" id="reg-email" placeholder="Seu e-mail">
            <input type="password" id="reg-pass" placeholder="Nova senha">"""

if ANTIGO_FORM in html:
    html = html.replace(ANTIGO_FORM, NOVO_FORM, 1)
    open("static/index.html", "w", encoding="utf-8").write(html)
    print("OK: campo de email adicionado no formulario!")
else:
    print("PROBLEMA: nao encontrei o trecho esperado do formulario. Nada foi alterado.")

print()

ANTIGO_JS = """async function doRegister(){
    var u=document.getElementById("reg-user").value.trim();
    var p=document.getElementById("reg-pass").value.trim();
    var r=await fetch(API+"/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
    var d=await r.json();
    if(d.msg){alert("Conta criada! Faca login.");}
    else{alert(d.detail||"Erro ao criar conta.");}
}"""

NOVO_JS = """async function doRegister(){
    var u=document.getElementById("reg-user").value.trim();
    var e=document.getElementById("reg-email").value.trim();
    var p=document.getElementById("reg-pass").value.trim();
    if(!e || !e.includes("@")){alert("Digite um e-mail valido!");return;}
    var r=await fetch(API+"/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,email:e,password:p})});
    var d=await r.json();
    if(d.msg){alert("Conta criada! Faca login.");}
    else{alert(typeof d.detail==="string"?d.detail:"Erro ao criar conta.");}
}"""

html2 = open("static/index.html", encoding="utf-8", errors="ignore").read()

if ANTIGO_JS in html2:
    html2 = html2.replace(ANTIGO_JS, NOVO_JS, 1)
    open("static/index.html", "w", encoding="utf-8").write(html2)
    print("OK: funcao doRegister atualizada!")
else:
    print("PROBLEMA: nao encontrei a funcao doRegister exata. Nada foi alterado nessa parte.")
