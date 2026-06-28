from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "minha-chave"
ALGORITHM = "HS256"

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)

def create_token(data: dict):
    expire = datetime.utcnow() + timedelta(hours=1)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
class VideoRequest(BaseModel):
    script: str
    imagem_url: str
    voz: str = "pt-BR-FranciscaNeural"

@router.post("/gerar-video")
def gerar_video(
    req: VideoRequest,
    user: str = Depends(get_current_user)
):
    import base64
    api_key = "ZGpyYWZmYTRAZ21haWwuY29t:pLaC2p5MWlykhjy9Zdgxi"
    
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "script": {
            "type": "text",
            "input": req.script,
            "provider": {
                "type": "microsoft",
                "voice_id": req.voz
            }
        },
        "source_url": req.imagem_url
    }
    
    response = requests.post(
        "https://api.d-id.com/talks",
        headers=headers,
        json=payload
    )
    
    data = response.json()
    talk_id = data.get("id")
    
    return {
        "talk_id": talk_id,
        "msg": "Video sendo gerado! Use o talk_id para buscar o resultado.",
        "usuario": user
    }