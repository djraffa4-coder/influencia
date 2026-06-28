conteudo = open("app/routes/auth.py", "r", encoding="utf-8").read()

novo_video = '''
class VideoRequest(BaseModel):
    script: str
    imagem_url: str
    voz: str = "pt-BR-FranciscaNeural"

@router.post("/gerar-video")
def gerar_video(req: VideoRequest, user: str = Depends(get_current_user)):
    HEYGEN_KEY = "sk_V2_hgu_k6YIJeIuuuL_iiuEltlGnSaiN5vuBmIzd6FJajh21u06"
    headers = {"X-Api-Key": HEYGEN_KEY, "Content-Type": "application/json"}
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "talking_photo",
                    "talking_photo_url": req.imagem_url
                },
                "voice": {
                    "type": "text",
                    "input_text": req.script,
                    "voice_id": "9da3f8b1064a4b5ba1236e84335c08df"
                }
            }
        ],
        "dimension": {"width": 720, "height": 1280}
    }
    response = requests.post(
        "https://api.heygen.com/v2/video/generate",
        headers=headers,
        json=payload
    )
    data = response.json()
    video_id = data.get("data", {}).get("video_id")
    return {"video_id": video_id, "msg": "Video sendo gerado!", "usuario": user}
'''

# Remove o codigo antigo do video e adiciona o novo
import re
conteudo_limpo = re.sub(
    r'class VideoRequest.*?return \{[^}]+\}',
    '',
    conteudo,
    flags=re.DOTALL
)

with open("app/routes/auth.py", "w", encoding="utf-8") as f:
    f.write(conteudo_limpo + novo_video)
print("HeyGen integrado!")