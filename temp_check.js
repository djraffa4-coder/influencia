
const API = "";
var token = "";
var perfilAtual = "rafaela";
var currentTalkId = "";
var uploadedImageB64 = "";

function showLogin(){
    document.getElementById("app-screen").style.display="none";
    document.getElementById("login-screen").style.display="flex";
}
function showApp(username){
    document.getElementById("login-screen").style.display="none";
    document.getElementById("app-screen").style.display="flex";
    document.getElementById("user-name-top").textContent=username;
    document.getElementById("user-avatar").textContent=username[0].toUpperCase();
}
function showRegister(){
    document.getElementById("register-section").style.display="block";
}
async function doLogin(){
    const u=document.getElementById("login-user").value.trim();
    const p=document.getElementById("login-pass").value.trim();
    const err=document.getElementById("login-err");
    err.style.display="none";
    try{
        const r=await fetch(API+"/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
        const d=await r.json();
        if(d.access_token){token=d.access_token;showApp(u);}
        else{err.textContent=d.detail||"Erro ao entrar.";err.style.display="block";}
    }catch(e){err.textContent="Erro ao conectar.";err.style.display="block";}
}
async function doRegister(){
    const u=document.getElementById("reg-user").value.trim();
    const p=document.getElementById("reg-pass").value.trim();
    const r=await fetch(API+"/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:u,password:p})});
    const d=await r.json();
    if(d.msg){alert("Conta criada! Faça login.");document.getElementById("register-section").style.display="none";}
    else{alert(d.detail||"Erro ao criar conta.");}
}
function doLogout(){token="";currentTalkId="";showLogin();}
function showPage(page, el){
    document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));
    document.querySelectorAll(".sidebar-item").forEach(i=>i.classList.remove("active"));
    document.getElementById("page-"+page).classList.add("active");
    if(el)el.classList.add("active");
}
function setExemplo(val){
    document.getElementById("produto").value=val;
    document.getElementById("char-count").textContent=val.length+"/100";
}
function selecionarPerfil(perfil,el){
    perfilAtual=perfil;
    document.querySelectorAll(".perfil-card").forEach(c=>c.classList.remove("ativo"));
    el.classList.add("ativo");
}
function handleUpload(input){
    const file=input.files[0];
    if(!file)return;
    const reader=new FileReader();
    reader.onload=function(e){
        uploadedImageB64=e.target.result.split(",")[1];
        document.getElementById("upload-thumb").src=e.target.result;
        document.getElementById("upload-name").textContent=file.name;
        document.getElementById("upload-size").textContent=(file.size/1024).toFixed(0)+" KB";
        document.getElementById("upload-preview-area").style.display="flex";
        document.getElementById("upload-area").style.display="none";
    };
    reader.readAsDataURL(file);
}
function removeUpload(){
    uploadedImageB64="";
    document.getElementById("file-input").value="";
    document.getElementById("upload-preview-area").style.display="none";
    document.getElementById("upload-area").style.display="block";
}
function showLoading(text){
    document.getElementById("loading-text").textContent=text||"Gerando com IA...";
    document.getElementById("loading-overlay").style.display="flex";
}
function hideLoading(){document.getElementById("loading-overlay").style.display="none";}
function verImagem(){
    const src=document.getElementById("img-gerada").src||document.getElementById("result-img").src;
    document.getElementById("modal-img-src").src=src;
    document.getElementById("modal-img").style.display="flex";
}
async function gerarScript(){
    const produto=document.getElementById("produto").value.trim();
    if(!produto){alert("Digite o produto!");return;}
    showLoading("Gerando script com IA...");
    try{
        const r=await fetch(API+"/gerar-script",{
            method:"POST",
            headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},
            body:JSON.stringify({
                produto:produto,
                nicho:document.getElementById("nicho").value,
                tom:document.getElementById("tom").value,
                perfil:perfilAtual
            })
        });
        const d=await r.json();
        if(d.script){
            document.getElementById("result-empty").style.display="none";
            document.getElementById("result-content").style.display="block";
            document.getElementById("result-script").textContent=d.script;
            document.getElementById("video-script").value=d.script;
        }else{alert("Erro ao gerar script.");}
    }catch(e){alert("Erro: "+e.message);}
    hideLoading();
}
function copiarScript(){
    navigator.clipboard.writeText(document.getElementById("result-script").textContent);
    alert("Script copiado!");
}
async function gerarImagem(){
    const produto=document.getElementById("img-produto")?document.getElementById("img-produto").value:"";
    showLoading("Gerando influenciadora com IA...");
    try{
        const r=await fetch(API+"/gerar-imagem",{
            method:"POST",
            headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},
            body:JSON.stringify({
                perfil:perfilAtual,
                produto:produto,
                imagem_produto_b64:uploadedImageB64,
                cabelo:document.getElementById('opt-cabelo')?document.getElementById('opt-cabelo').value:'',
                olhos:document.getElementById('opt-olhos')?document.getElementById('opt-olhos').value:'',
                etnia:document.getElementById('opt-etnia')?document.getElementById('opt-etnia').value:'',
                cenario:document.getElementById('opt-cenario')?document.getElementById('opt-cenario').value:''
            })
        });
        const d=await r.json();
        if(d.url){
            const url=d.url;
            document.getElementById("img-gerada").src=url;
            document.getElementById("img-download").href=url;
            document.getElementById("img-result").style.display="block";
            document.getElementById("result-img").src=url;
            document.getElementById("result-img-download").href=url;
            document.getElementById("result-img-area").style.display="block";
            document.getElementById("video-imagem").value=window.location.origin+url;
        }else{alert("Erro: "+JSON.stringify(d));}
    }catch(e){alert("Erro: "+e.message);}
    hideLoading();
}
async function enviarVideo(){
    const script=document.getElementById("video-script").value.trim();
    const imagem=document.getElementById("video-imagem").value.trim();
    const voz=document.getElementById("video-voz").value;
    if(!script||!imagem){alert("Preencha o script e a URL da imagem!");return;}
    showLoading("Enviando para gerar vídeo...");
    try{
        const r=await fetch(API+"/gerar-video",{
            method:"POST",
            headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},
            body:JSON.stringify({script,imagem_url:imagem,voz})
        });
        const d=await r.json();
        if(d.video_id){
            currentTalkId=d.video_id;
            document.getElementById("status-text").textContent="Vídeo sendo processado! ID: "+d.video_id;
            document.getElementById("status-msg").style.display="block";
        }else{alert("Erro: "+JSON.stringify(d));}
    }catch(e){alert("Erro: "+e.message);}
    hideLoading();
}
async function verificarVideo(){
    if(!currentTalkId){alert("Nenhum vídeo em processamento!");return;}
    showLoading("Verificando vídeo...");
    try{
        const r=await fetch("https://api.heygen.com/v1/video_status.get?video_id="+currentTalkId,{
            headers:{"X-Api-Key":"sk_V2_hgu_k6YIJeIuuuL_iiuEltlGnSaiN5vuBmIzd6FJajh21u06"}
        });
        const d=await r.json();
        const status=d.data?.status;
        if(status==="completed"){
            const url=d.data?.video_url;
            document.getElementById("status-text").innerHTML='✅ Pronto! <a href="'+url+'" target="_blank" style="color:#a78bfa;">Clique aqui para ver o vídeo</a>';
        }else{
            document.getElementById("status-text").textContent="Status: "+status+". Aguarde e tente novamente.";
        }
    }catch(e){alert("Erro: "+e.message);}
    hideLoading();
}
async function gerarCombo(){
    alert("Em breve! Use as abas Scripts e Influenciadora separadamente por enquanto.");
}

function salvarScript(){
    const texto = document.getElementById("result-script").textContent;
    const produto = document.getElementById("produto").value;
    if(!texto) return;
    const scripts = JSON.parse(localStorage.getItem("influencia_scripts")||"[]");
    scripts.unshift({produto, texto, data: new Date().toLocaleDateString("pt-BR")});
    localStorage.setItem("influencia_scripts", JSON.stringify(scripts));
    renderScripts();
    alert("Script salvo!");
}
function renderScripts(){
    const scripts = JSON.parse(localStorage.getItem("influencia_scripts")||"[]");
    const lista = document.getElementById("lista-scripts");
    if(!lista) return;
    if(scripts.length===0){
        lista.innerHTML='<div style="color:#555;text-align:center;padding:40px;">Nenhum script salvo ainda.</div>';
        return;
    }
    lista.innerHTML = scripts.map((s,i)=>'<div style="background:#13131f;border:1px solid #1e1e35;border-radius:16px;padding:20px;"><div style="display:flex;justify-content:space-between;margin-bottom:12px;"><div style="font-weight:700;">'+s.produto+'</div><div style="color:#555;font-size:12px;">'+s.data+'</div></div><div style="color:#aaa;font-size:14px;line-height:1.6;">'+s.texto+'</div><div style="display:flex;gap:8px;margin-top:12px;"><button class="result-btn" onclick="navigator.clipboard.writeText(\''+s.texto.replace(/\'/g,\"\\\'\")+ \'\')">📋 Copiar</button><button class="result-btn" style="color:#f87171;border-color:#f87171;" onclick="deletarScript('+i+')">🗑️ Deletar</button></div></div>').join("");
}
function deletarScript(i){
    const scripts = JSON.parse(localStorage.getItem("influencia_scripts")||"[]");
    scripts.splice(i,1);
    localStorage.setItem("influencia_scripts", JSON.stringify(scripts));
    renderScripts();
}

