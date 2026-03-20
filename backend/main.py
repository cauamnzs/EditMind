from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from database import engine, Base

Base.metadata.create_all(bind=engine) 

# Importando as Rotas (AGORA COM TODAS AS PEÇAS DO EXODIA)
from routes import upload_routes, ai_routes

app = FastAPI(title="EditMind API")

# 1º - PERMISSÃO DE CORS VEM PRIMEIRO! (Absolutamente crucial)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2º - MONTAR AS PASTAS DEPOIS DO CORS! (Para os vídeos herdarem a permissão)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configuração de Pastas (Garante que tudo exista)
os.makedirs("uploads/videos", exist_ok=True)
os.makedirs("uploads/audios", exist_ok=True)
os.makedirs("uploads/cortes", exist_ok=True) 

# Plugando as Rotas no Servidor
app.include_router(upload_routes.router)
app.include_router(ai_routes.router)     

@app.get("/")
def root():
    return {"mensagem": "EditMind rodando 100% com Arquitetura Limpa e Motor Turbo!"}