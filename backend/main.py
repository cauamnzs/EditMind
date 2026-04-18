"""
EditMind API - FastAPI Application
Arquitetura otimizada para alta performance
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Database
from database import engine, Base
Base.metadata.create_all(bind=engine) 

# Rotas
from routes import upload_routes, ai_routes, auth_routes, sse_routes

# ==========================================
# APP CONFIGURATION
# ==========================================
app = FastAPI(
    title="EditMind API",
    description="API para automação de cortes virais de vídeos com IA",
    version="1.0.0"
)

# CORS - Configurado para Vercel + Ngrok
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://mind.vercel.app",
        "https://edit-mind.vercel.app",
        "https://*.vercel.app",
        "https://shelley-filar-alona.ngrok-free.dev",
        "https://*.ngrok-free.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "ngrok-skip-browser-warning"],
    expose_headers=["*"],
    max_age=86400,
)

# ==========================================
# STATIC FILES
# ==========================================
# Configuração de Pastas
os.makedirs("uploads/videos", exist_ok=True)
os.makedirs("uploads/audios", exist_ok=True)
os.makedirs("uploads/cortes", exist_ok=True)
os.makedirs("uploads/temp_clips", exist_ok=True)
os.makedirs("uploads/broll", exist_ok=True)

# Monta pastas de uploads (DEPOIS do CORS)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ==========================================
# ROUTES
# ==========================================
app.include_router(auth_routes.router)
app.include_router(upload_routes.router)
app.include_router(ai_routes.router)
app.include_router(sse_routes.router)

# ==========================================
# ROOT ENDPOINT
# ==========================================
@app.get("/")
def root():
    return {
        "mensagem": "EditMind API rodando",
        "versao": "1.0.0",
        "status": "online",
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": str(os.times())
    }