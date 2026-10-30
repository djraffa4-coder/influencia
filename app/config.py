import os

# ── Variaveis OBRIGATORIAS (repositorio publico: nunca usar valor padrao no codigo) ──
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY nao configurada! Configure a variavel de ambiente no Render.")

ADMIN_KEY = os.getenv("ADMIN_KEY")
if not ADMIN_KEY:
    raise RuntimeError("ADMIN_KEY nao configurada! Configure a variavel de ambiente no Render.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias

# URL base da aplicacao no Render, sem barra no final (ex: https://influencia.onrender.com).
# Usada nos back_urls do Mercado Pago, no link de redefinicao de senha e no CORS.
APP_URL = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")

# ── Chaves de servicos externos ──
GEMINI_KEY = os.getenv("GEMINI_KEY", "")
STABILITY_KEY = os.getenv("STABILITY_KEY", "")
HEYGEN_KEY = os.getenv("HEYGEN_KEY", "")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "djraffa4@gmail.com")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
META_PIXEL_ID = os.getenv("META_PIXEL_ID", "")
META_CAPI_ACCESS_TOKEN = os.getenv("META_CAPI_ACCESS_TOKEN", "")
TIKTOK_PIXEL_ID = os.getenv("TIKTOK_PIXEL_ID", "")

# Maximo de demos gratis (pagina inicial, sem login) geradas por dia somando todos os visitantes.
# Protege o custo do Gemini caso alguem burle o limite por IP.
DEMO_LIMITE_DIARIO = int(os.getenv("DEMO_LIMITE_DIARIO", "100"))

# Timeout (segundos) das chamadas as APIs de IA
TIMEOUT_IA = 60

# ── Catalogo de planos (preco definido AQUI, no backend — nao confia no frontend) ──
PLANOS_CONFIG = {
    "kit_teste": {"title": "Kit Teste - InfluencIA", "price": 47.00, "plano_interno": "starter"},
    "kit_pro": {"title": "Kit Criador PRO - InfluencIA", "price": 97.00, "plano_interno": "pro"},
    "kit_agencia": {"title": "Kit Agencia - InfluencIA", "price": 197.00, "plano_interno": "business"},
}

# ── Limites mensais por plano (unica fonte; usado em /creditos e na geracao) ──
LIMITES = {
    "free": {"scripts": 3, "imagens": 2, "imagens_pro": 0, "videos": 0},
    "starter": {"scripts": 50, "imagens": 20, "imagens_pro": 5, "videos": 2},
    "pro": {"scripts": 150, "imagens": 60, "imagens_pro": 25, "videos": 10},
    "business": {"scripts": 400, "imagens": 200, "imagens_pro": 60, "videos": 30},
}
