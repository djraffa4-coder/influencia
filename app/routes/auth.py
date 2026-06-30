import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import requests
from app.dependencies import get_current_user
from app.database import SessionLocal
from app.models import User as DBUser

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

LIMITES = {
    "free": {"scripts": 3, "imagens": 2, "imagens_pro": 0},
    "pro": {"scripts": 150, "imagens": 60, "imagens_pro": 25},
    "business": {"scripts": 400, "imagens": 200, "imagens_pro": 60}
}

def verificar_creditos(db_user, db, tipo):
    mes_atual = datetime.now().strftime("%Y-%m")
    if db_user.mes_referencia != mes_atual:
        db_user.scripts_usados = 0
        db_user.imagens_usadas = 0
        db_user.imagens_pro_usadas = 0
        db_user.mes_referencia = mes_atual
        db.commit()
    limite = LIMITES.get(db_user.plano or "free", LIMITES["free"])
    if tipo == "scripts" and db_user.scripts_usados >= limite["scripts"]:
        raise HTTPException(status_code=403, detail="Limite de scripts atingido neste mes. Faca upgrade do seu plano!")
    if tipo == "imagens" and db_user.imagens_usadas >= limite["imagens"]:
        raise HTTPException(status_code=403, detail="Limite de imagens atingido neste mes. Faca upgrade do seu plano!")
    if tipo == "imagens_pro" and db_user.imagens_pro_usadas >= limite["imagens_pro"]:
        raise HTTPException(status_code=403, detail="Limite de Imagens Pro atingido neste mes. Faca upgrade do seu plano!")

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

class ScriptRequest(BaseModel):
    produto: str
    nicho: str = "moda"
    tom: str = "animado"
    perfil: str = "rafaela"

@router.post("/gerar-script")
def gerar_script(req: ScriptRequest, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.username == user).first()
    verificar_creditos(db_user, db, "scripts")

    perfil = PERFIS.get(req.perfil, PERFIS["rafaela"])
    prompt = f"""Voce e {perfil['nome']}, um influencer digital brasileiro do TikTok.

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

Agora crie para: {req.produto}"""
    GEMINI_KEY = os.getenv("GEMINI_KEY", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    data = response.json()
    script = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Erro ao gerar script")

    db_user.scripts_usados += 1
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

@router.post("/gerar-imagem")
def gerar_imagem(req: ImagemRequest, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    import uuid, base64 as b64mod, tempfile, os

    db_user = db.query(DBUser).filter(DBUser.username == user).first()
    eh_pro = bool(req.imagem_produto_b64)
    verificar_creditos(db_user, db, "imagens_pro" if eh_pro else "imagens")

    perfil = PERFIS.get(req.perfil, PERFIS["rafaela"])

    if req.imagem_produto_b64:
        GEMINI_KEY = os.getenv("GEMINI_KEY", "")
        url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
        payload_gemini = {
            "contents": [{
                "parts": [
                    {"text": "Descreva esse produto em ingles em uma linha curta para usar em um prompt de imagem. Apenas a descricao do produto, sem mais nada."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": req.imagem_produto_b64}}
                ]
            }]
        }
        r = requests.post(url_gemini, json=payload_gemini)
        descricao_produto = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", req.produto).strip()
    else:
        descricao_produto = req.produto

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
        extras_list = [x for x in [req.cabelo, req.olhos, req.cenario] if x]
        extras = ", ".join(extras_list)
        prompt = base + (", " + extras if extras else "")

    produto_txt = f", holding a {descricao_produto} in her hand, the {descricao_produto} clearly visible, showing the {descricao_produto} to camera, TikTok product review, product placement, {descricao_produto} in focus, viral content" if descricao_produto else ""
    prompt = prompt + produto_txt
    if descricao_produto:
        prompt = f"product photography, {descricao_produto} clearly visible, " + prompt

    if req.imagem_produto_b64:
        GEMINI_KEY = os.getenv("GEMINI_KEY", "")
        url_imagen = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key={GEMINI_KEY}"
        perfil_desc = perfil["prompt"] if req.perfil != "custom" else f"{req.custom_etnia}, {req.custom_idade or '25'} years old, {req.custom_cabelo}, {req.custom_olhos}"
        payload_imagen = {
            "contents": [{
                "parts": [
                    {"text": f"Generate a photorealistic portrait of a beautiful Brazilian woman, {perfil_desc}. She is holding and showing this exact product to the camera. The product must appear exactly as in the reference image with same colors, same logo, same details, same brand. Clean modern background, professional photography, no text, no social media icons, no watermarks, no overlays, photorealistic, 8k quality."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": req.imagem_produto_b64}}
                ]
            }],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
        }
        r_imagen = requests.post(url_imagen, json=payload_imagen)
        data_imagen = r_imagen.json()
        parts = data_imagen.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        img_data = None
        for part in parts:
            if "inlineData" in part:
                img_data = b64mod.b64decode(part["inlineData"]["data"])
                break
        if img_data:
            img_id = str(uuid.uuid4())
            path = f"static/imagens/{img_id}.jpg"
            with open(path, "wb") as f:
                f.write(img_data)
            if eh_pro:
                db_user.imagens_pro_usadas += 1
            else:
                db_user.imagens_usadas += 1
            db.commit()
            return {"url": f"/static/imagens/{img_id}.jpg", "usuario": user}
        else:
            return {"erro": "Gemini nao retornou imagem", "detalhe": str(data_imagen)[:300]}
    else:
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={"authorization": f'Bearer {os.getenv("STABILITY_KEY")}', "accept": "image/*"},
            files={"none": ""},
            data={"prompt": prompt, "aspect_ratio": "2:3", "output_format": "jpeg"}
        )

    if response.status_code == 200:
        img_id = str(uuid.uuid4())
        path = f"static/imagens/{img_id}.jpg"
        with open(path, "wb") as f:
            f.write(response.content)
        db_user.imagens_usadas += 1
        db.commit()
        return {"url": f"/static/imagens/{img_id}.jpg", "usuario": user}
    return {"erro": str(response.text), "status": response.status_code}

class VideoRequest(BaseModel):
    script: str
    imagem_url: str
    voz: str = "pt-BR-FranciscaNeural"

@router.post("/gerar-video")
def gerar_video(req: VideoRequest, user: str = Depends(get_current_user)):
    HEYGEN_KEY = os.getenv("HEYGEN_KEY")
    headers = {"X-Api-Key": HEYGEN_KEY, "Content-Type": "application/json"}
    payload = {
        "video_inputs": [{"character": {"type": "talking_photo", "talking_photo_url": req.imagem_url}, "voice": {"type": "text", "input_text": req.script, "voice_id": "9da3f8b1064a4b5ba1236e84335c08df"}}],
        "dimension": {"width": 720, "height": 1280}
    }
    response = requests.post("https://api.heygen.com/v2/video/generate", headers=headers, json=payload)
    data = response.json()
    video_id = data.get("data", {}).get("video_id")
    return {"video_id": video_id, "msg": "Video sendo gerado!", "usuario": user}

@router.get("/verificar-video")
def verificar_video(video_id: str, user: str = Depends(get_current_user)):
    HEYGEN_KEY = os.getenv("HEYGEN_KEY")
    headers = {"X-Api-Key": HEYGEN_KEY}
    response = requests.get(f"https://api.heygen.com/v2/video/{video_id}", headers=headers)
    data = response.json()
    status = data.get("data", {}).get("status", "")
    video_url = data.get("data", {}).get("video_url", "")
    return {"status": status, "video_url": video_url}


