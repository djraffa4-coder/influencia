import requests
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import HEYGEN_KEY, LIMITES, STABILITY_KEY, TIMEOUT_IA
from app.database import get_db
from app.ia import gemini_imagem, gemini_texto, salvar_imagem
from app.models import Imagem, User as DBUser
from app.routes.contas import renovar_mes
from app.seguranca import get_current_user

router = APIRouter()

MENSAGENS_LIMITE = {
    "scripts": "Limite de scripts atingido neste mes. Faca upgrade do seu plano!",
    "imagens": "Limite de imagens atingido neste mes. Faca upgrade do seu plano!",
    "imagens_pro": "Limite de Imagens Pro atingido neste mes. Faca upgrade do seu plano!",
    "videos": "Limite de videos atingido neste mes. Faca upgrade do seu plano!",
}
CAMPO_USO = {
    "scripts": "scripts_usados",
    "imagens": "imagens_usadas",
    "imagens_pro": "imagens_pro_usadas",
    "videos": "videos_usados",
}

def carregar_usuario(db, user):
    db_user = db.query(DBUser).filter(DBUser.username == user).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    return db_user

def verificar_creditos(db_user, db, tipo):
    renovar_mes(db_user, db)
    limite = LIMITES.get(db_user.plano or "free", LIMITES["free"])
    if (getattr(db_user, CAMPO_USO[tipo]) or 0) >= limite[tipo]:
        raise HTTPException(status_code=403, detail=MENSAGENS_LIMITE[tipo])

def consumir_credito(db_user, tipo):
    """So e chamado depois que a geracao deu certo — falha nao gasta credito."""
    campo = CAMPO_USO[tipo]
    setattr(db_user, campo, (getattr(db_user, campo) or 0) + 1)

ERRO_IMAGEM = "A IA nao conseguiu gerar a imagem agora. Tente novamente — seu credito nao foi descontado."

PERFIS = {
    "rafaela": {
        "nome": "Rafaela Morita",
        "prompt": "26 year old Brazilian Japanese woman from Rio de Janeiro, long straight black hair, almond eyes, confident elegant expression, fashion influencer, TikTok creator, modern outfit, ring light reflection, photorealistic, 8k, studio lighting"
    },
    "bianca": {
        "nome": "Bianca Alves",
        "prompt": "26 year old Brazilian blonde woman, light eyes, radiant smile, beauty and lifestyle influencer, TikTok creator, trendy outfit, modern apartment background, ring light reflection, best friend energy, photorealistic, 8k, natural lighting"
    },
    "camila": {
        "nome": "Camila Rocha",
        "prompt": "28 year old Brazilian woman with curly dark hair, athletic body, strong motivational expression, fitness influencer, TikTok creator, sports outfit, gym background, ring light reflection, powerful energy, photorealistic, 8k, dynamic lighting"
    },
    "isabella": {
        "nome": "Isabella Cruz",
        "prompt": "30 year old Brazilian Black woman, natural afro hair, elegant sophisticated posture, luxury lifestyle influencer, TikTok creator, premium outfit, luxury apartment background, ring light reflection, confident expression, photorealistic, 8k, cinematic lighting"
    },
    "larissa": {
        "nome": "Larissa Santos",
        "prompt": "25 year old Brazilian redhead woman, modern glasses, intelligent friendly expression, tech and education influencer, TikTok creator, smart casual outfit, modern office background, ring light reflection, approachable smile, photorealistic, 8k, soft lighting"
    },
    "rafael": {
        "nome": "Rafael Costa",
        "prompt": "28 year old Black Brazilian man, muscular athletic build, defined abs, short fade haircut, strong jawline, confident powerful expression, fitness influencer, TikTok creator, shirtless or fitted sportswear, gym background, photorealistic, 8k, dynamic lighting"
    },
    "lucas": {
        "nome": "Lucas Mendes",
        "prompt": "27 year old Brazilian man, tanned skin, messy beach wave hair, relaxed laid-back vibe, casual confident smile, streetwear style, urban lifestyle influencer, TikTok creator, Rio de Janeiro street background, photorealistic, 8k, natural lighting"
    },
    "pedro": {
        "nome": "Pedro Alves",
        "prompt": "29 year old German blonde man, light blonde hair, piercing blue eyes, strong muscular build, chiseled jawline, athletic European look, fitness and lifestyle influencer, TikTok creator, modern gym or outdoor background, photorealistic, 8k, dynamic lighting"
    },
    "mateus": {
        "nome": "Mateus Lima",
        "prompt": "26 year old Japanese man, sleek black hair, sharp seductive eyes, refined elegant features, alluring confident expression, fashion and lifestyle influencer, TikTok creator, stylish modern outfit, minimalist background, photorealistic, 8k, cinematic lighting"
    }
}

MASCULINOS = ["rafael", "lucas", "pedro", "mateus"]

class ScriptRequest(BaseModel):
    produto: str
    nicho: str = "moda"
    tom: str = "animado"
    perfil: str = "rafaela"
    prompt_customizado: str = ""

@router.post("/gerar-script")
def gerar_script(req: ScriptRequest, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = carregar_usuario(db, user)
    verificar_creditos(db_user, db, "scripts")

    perfil = PERFIS.get(req.perfil, PERFIS["rafaela"])
    if req.prompt_customizado and req.prompt_customizado.strip():
        prompt = req.prompt_customizado.strip()
    else:
        prompt = f"""Voce e {perfil['nome']}, um influencer digital brasileiro do TikTok.

Crie um script de venda COMPLETO E DETALHADO de 30 a 40 segundos falados para o produto: {req.produto}.
Nicho: {req.nicho}. Tom: {req.tom}.

FORMATO OBRIGATORIO: divida o script em blocos com marcacao de tempo, EXATAMENTE assim:

[0-3s] (gancho): texto do gancho aqui
[3-10s] (problema/dor): texto aqui
[10-20s] (solucao/beneficios): texto aqui, pode ter 2-3 frases detalhando beneficios reais e especificos
[20-28s] (prova social/diferencial): texto aqui
[28-35s] (CTA): texto aqui

REGRAS OBRIGATORIAS:
- Cada bloco comeca com a marcacao de tempo entre colchetes e o rotulo entre parenteses, seguido de dois pontos, depois o texto
- Gancho deve surpreender ou gerar curiosidade nos primeiros 3 segundos
- Bloco de solucao deve ser o mais detalhado, com beneficios especificos e reais do produto (nao generico)
- Inclua um bloco de prova social ou diferencial (ex: "milhares ja usam", "unico que faz X", depoimento fictício breve)
- CTA final urgente e direto (ex: "Link na bio!", "Corre la!", "Garante ja!")
- Linguagem natural e fluida de TikTok brasileiro, como se estivesse falando pra camera
- SEM asteriscos, SEM indicacoes de cena adicionais alem da marcacao de tempo pedida
- Uma quebra de linha entre cada bloco

Exemplo de formato correto para um perfume:
[0-3s] (gancho): Gente, para tudo que eu preciso te contar uma coisa!
[3-10s] (problema): Voce ja passou vergonha porque o perfume some depois de duas horas?
[10-20s] (solucao): Esse aqui dura o dia INTEIRO, literalmente sai de casa de manha e chega em casa a noite ainda perfumado. E o frasco e lindo, da vontade de deixar exposto.
[20-28s] (prova social): Ja vendi mais de 500 unidades esse mes e o pessoal so elogia.
[28-35s] (CTA): Corre no link da bio antes que esgote de novo!

Agora crie para: {req.produto}"""

    script = gemini_texto([{"text": prompt}])
    if not script:
        raise HTTPException(status_code=502, detail="A IA nao conseguiu gerar o script agora. Tente novamente — seu credito nao foi descontado.")

    consumir_credito(db_user, "scripts")
    db.commit()
    return {"script": script, "produto": req.produto, "usuario": user}

class ImagemRequest(BaseModel):
    perfil: str = "rafaela"
    produto: str = ""
    imagem_produto_b64: str = ""
    cabelo: str = ""
    olhos: str = ""
    etnia: str = ""
    cenario: str = ""
    custom_nome: str = ""
    custom_idade: str = ""
    custom_genero: str = "feminino"
    custom_etnia: str = ""
    custom_cabelo: str = ""
    custom_olhos: str = ""
    custom_estilo: str = ""
    custom_cenario: str = ""
    custom_expressao: str = ""
    custom_extra: str = ""
    prompt_customizado: str = ""

@router.post("/gerar-imagem")
def gerar_imagem(req: ImagemRequest, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = carregar_usuario(db, user)
    eh_pro = bool(req.imagem_produto_b64)
    tipo = "imagens_pro" if eh_pro else "imagens"
    verificar_creditos(db_user, db, tipo)

    perfil = PERFIS.get(req.perfil, PERFIS["rafaela"])
    eh_masculino = (req.perfil in MASCULINOS) or (req.perfil == "custom" and req.custom_genero == "masculino")

    # ── Influencer PRO: usa a foto real do produto como referencia ──
    if eh_pro:
        foto_produto = {"inline_data": {"mime_type": "image/jpeg", "data": req.imagem_produto_b64}}
        if req.prompt_customizado and req.prompt_customizado.strip():
            texto = req.prompt_customizado.strip()
        else:
            perfil_desc = perfil["prompt"] if req.perfil != "custom" else f"{req.custom_etnia}, {req.custom_idade or '25'} years old, {req.custom_cabelo}, {req.custom_olhos}"
            pessoa = "man" if req.perfil in MASCULINOS else "beautiful woman"
            pronome = "He" if req.perfil in MASCULINOS else "She"
            texto = f"Generate a photorealistic portrait of a {pessoa}, {perfil_desc}. {pronome} is holding and showing this exact product to the camera. The product must appear exactly as in the reference image with same colors, same logo, same details, same brand. Clean modern background, professional photography, no text, no social media icons, no watermarks, no overlays, photorealistic, 8k quality."
        img_data = gemini_imagem([{"text": texto}, foto_produto])
        if not img_data:
            raise HTTPException(status_code=502, detail=ERRO_IMAGEM)
        url = salvar_imagem(db, img_data, user)
        consumir_credito(db_user, tipo)
        db.commit()
        return {"url": url, "usuario": user}

    # ── Imagem comum: monta o prompt a partir do perfil escolhido ──
    if req.perfil == "custom":
        idade = req.custom_idade or "25"
        extra = f", {req.custom_extra}" if req.custom_extra else ""
        genero = "man" if req.custom_genero == "masculino" else "woman"
        prompt = f"{req.custom_etnia} {genero}, {idade} years old, {req.custom_cabelo}, {req.custom_olhos}, {req.custom_expressao}, {req.custom_estilo}, {req.custom_cenario}, TikTok influencer, photorealistic, 8k, high detail{extra}"
    else:
        if req.etnia:
            base = f"{req.etnia}, TikTok influencer, beautiful, photorealistic, 8k, studio lighting"
        else:
            base = perfil["prompt"]
        extras = ", ".join(x for x in [req.cabelo, req.olhos, req.cenario] if x)
        prompt = base + (", " + extras if extras else "")

    if req.produto:
        prompt += f", holding a {req.produto} in hand, product clearly visible, TikTok product review style"

    if eh_masculino:
        prompt = "photo of a man, male model, masculine features, " + prompt
        negative_prompt = "woman, female, feminine features, " + NEGATIVE_BASE
    else:
        negative_prompt = NEGATIVE_BASE

    if (db_user.plano or "free") == "free":
        img_data = gemini_imagem([{"text": f"Generate a photorealistic portrait of a {prompt}. Clean modern background, professional photography, no text, no social media icons, no watermarks, no overlays, photorealistic, 8k quality."}])
    else:
        img_data = gerar_stability(prompt, negative_prompt)

    if not img_data:
        raise HTTPException(status_code=502, detail=ERRO_IMAGEM)
    url = salvar_imagem(db, img_data, user)
    consumir_credito(db_user, tipo)
    db.commit()
    return {"url": url, "usuario": user}

NEGATIVE_BASE = "deformed, disfigured, extra limbs, extra fingers, mutated hands, bad anatomy, long neck, elongated neck, distorted body, extra heads, duplicate, blurry, low quality, watermark, text, out of frame, cropped, malformed limbs"

def gerar_stability(prompt, negative_prompt):
    try:
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={"authorization": f"Bearer {STABILITY_KEY}", "accept": "image/*"},
            files={"none": ""},
            data={"prompt": prompt, "negative_prompt": negative_prompt, "aspect_ratio": "2:3", "output_format": "jpeg"},
            timeout=TIMEOUT_IA,
        )
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao chamar Stability: {e}")
        return None
    if response.status_code != 200:
        print(f"[ERRO] Stability respondeu {response.status_code}: {response.text[:300]}")
        return None
    return response.content

@router.get("/imagens/{nome}")
def ver_imagem(nome: str, db: Session = Depends(get_db)):
    img = db.query(Imagem).filter(Imagem.id == nome.rsplit(".", 1)[0]).first()
    if not img:
        raise HTTPException(status_code=404, detail="Imagem nao encontrada")
    return Response(content=img.dados, media_type=img.mime or "image/jpeg",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})

class VideoRequest(BaseModel):
    script: str
    imagem_url: str
    voz: str = "pt-BR-FranciscaNeural"

@router.post("/gerar-video")
def gerar_video(req: VideoRequest, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = carregar_usuario(db, user)
    verificar_creditos(db_user, db, "videos")

    headers = {"X-Api-Key": HEYGEN_KEY, "Content-Type": "application/json"}
    payload = {
        "video_inputs": [{"character": {"type": "talking_photo", "talking_photo_url": req.imagem_url}, "voice": {"type": "text", "input_text": req.script, "voice_id": "9da3f8b1064a4b5ba1236e84335c08df"}}],
        "dimension": {"width": 720, "height": 1280}
    }
    try:
        response = requests.post("https://api.heygen.com/v2/video/generate", headers=headers, json=payload, timeout=TIMEOUT_IA)
        data = response.json()
    except Exception as e:
        print(f"[ERRO] Falha ao chamar HeyGen: {e}")
        raise HTTPException(status_code=502, detail="Erro ao enviar o video, tente novamente")
    video_id = (data.get("data") or {}).get("video_id")
    if not video_id:
        print(f"[ERRO] HeyGen sem video_id: {str(data)[:300]}")
        raise HTTPException(status_code=502, detail="Nao foi possivel iniciar o video agora. Tente novamente — seu credito nao foi descontado.")

    consumir_credito(db_user, "videos")
    db.commit()
    return {"video_id": video_id, "msg": "Video sendo gerado!", "usuario": user}

@router.get("/verificar-video")
def verificar_video(video_id: str, user: str = Depends(get_current_user)):
    try:
        response = requests.get(f"https://api.heygen.com/v2/video/{video_id}", headers={"X-Api-Key": HEYGEN_KEY}, timeout=30)
        data = response.json().get("data") or {}
    except Exception as e:
        print(f"[ERRO] Falha ao consultar HeyGen: {e}")
        raise HTTPException(status_code=502, detail="Erro ao consultar o video, tente novamente")
    return {"status": data.get("status", ""), "video_url": data.get("video_url", "")}
