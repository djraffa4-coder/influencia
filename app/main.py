from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_URL, GOOGLE_CLIENT_ID, META_PIXEL_ID, TIKTOK_PIXEL_ID
from app.database import criar_tabelas
from app.routes import admin, contas, demo, geracao, pagamentos

app = FastAPI()

# O frontend e servido pelo proprio backend (mesma origem); so libera o dominio do app.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[APP_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

criar_tabelas()


@app.get("/")
@app.head("/")
def raiz():
    return RedirectResponse(url="/app")

@app.get("/app")
@app.head("/app")
def frontend():
    return FileResponse("static/index.html")

@app.get("/config-publica")
def config_publica():
    return {
        "google_client_id": GOOGLE_CLIENT_ID,
        "meta_pixel_id": META_PIXEL_ID,
        "tiktok_pixel_id": TIKTOK_PIXEL_ID
    }

@app.get("/privacidade")
def privacidade():
    return FileResponse("static/privacidade.html")

@app.get("/termos")
def termos():
    return FileResponse("static/termos.html")

@app.get("/saude")
def saude():
    return {"status": "ok"}


app.include_router(contas.router)
app.include_router(geracao.router)
app.include_router(pagamentos.router)
app.include_router(admin.router)
app.include_router(demo.router)
