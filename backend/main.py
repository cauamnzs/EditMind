from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Importando as Rotas
from routes import upload_routes

app = FastAPI(title="EditMind API")

# Permissão de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração de Pastas
os.makedirs("uploads/videos", exist_ok=True)
os.makedirs("uploads/audios", exist_ok=True)

# Plugando as Rotas
app.include_router(upload_routes.router)

@app.get("/")
def root():
    return {"mensagem": "EditMind rodando 100% com Arquitetura Limpa!"}