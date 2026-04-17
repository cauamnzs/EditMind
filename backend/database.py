from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Float
from sqlalchemy.types import JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from contextlib import contextmanager
from datetime import datetime
import threading
import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# CONFIGURAÇÃO DE BANCO — Lê do .env, fallback para SQLite local
# Para usar PostgreSQL em produção: DATABASE_URL=postgresql://user:pass@host/db
# ==========================================
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./editmind.db")

_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # SQLite: não suporta QueuePool nem conexões paralelas reais
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # Garante SSL obrigatório para Supabase/nuvem (injetado automaticamente)
    _db_url = SQLALCHEMY_DATABASE_URL
    if "sslmode" not in _db_url:
        _separator = "&" if "?" in _db_url else "?"
        _db_url = f"{_db_url}{_separator}sslmode=require"

    # PostgreSQL / Supabase: pooling otimizado para Supavisor (Transaction Pooler)
    engine = create_engine(
        _db_url,
        poolclass=QueuePool,
        pool_size=5,               # Supabase free tier suporta ~20 conexões simultâneas
        max_overflow=10,           # Conexões extras sob demanda
        pool_timeout=30,           # Timeout aguardando conexão disponível
        pool_recycle=300,          # Recicla conexões a cada 5min (evita timeout do Supavisor)
        pool_pre_ping=True,        # Testa conexão antes de usar (evita conexões mortas)
        echo=False
    )

print(f"🗄️  [Database] Engine iniciado: {'SQLite (local)' if _is_sqlite else 'PostgreSQL/Supabase (produção)'}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Thread-local storage para sessões
_thread_local = threading.local()

@contextmanager
def get_db_session():
    """Context manager para sessões de banco seguras em concorrência."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_db():
    """Função para injeção de dependência FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# MODELOS DE DADOS
# ==========================================
class VideoProcessado(Base):
    __tablename__ = "videos_processados"
    id = Column(String, primary_key=True, index=True)
    nome_original = Column(String)
    caminho_video = Column(String)
    caminho_audio = Column(String)
    transcricao = Column(Text)
    metadados_edicao = Column(JSON, nullable=True)      # JSON completo do Editor Chefe v2
    status = Column(String, default="processando")      # processando | pronto | erro
    export_log = Column(JSON, nullable=True)            # log de erros/etapas do pipeline
    duracao_segundos = Column(Float, nullable=True)     # duração do bruto em segundos
    criado_em = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, nullable=True)             # Para futuro multi-tenant

class ClipGerado(Base):
    __tablename__ = "clips_gerados"
    id = Column(String, primary_key=True, index=True)           # output_id do gerar-corte-viral
    video_id = Column(String, index=True)                        # FK para videos_processados.id
    cut_id = Column(Integer, nullable=True)                      # cut_id do Editor Chefe
    titulo = Column(String, nullable=True)
    viral_score = Column(Integer, nullable=True)
    gancho = Column(Text, nullable=True)
    motivo = Column(Text, nullable=True)
    keyword_broll = Column(String, nullable=True)
    raw_start = Column(String, nullable=True)                    # HH:MM:SS.mmm
    raw_end = Column(String, nullable=True)
    duracao_editada = Column(Float, nullable=True)               # segundos editados
    caminho_clip = Column(String, nullable=True)                 # path do .mp4 gerado
    caminho_vtt = Column(String, nullable=True)                  # path do .vtt gerado
    segments_to_keep = Column(JSON, nullable=True)               # [{start, end}, ...]
    synced_transcript = Column(JSON, nullable=True)              # [{start_offset, end_offset, text}, ...]
    status = Column(String, default="pendente")                  # pendente | exportando | pronto | erro
    export_log = Column(JSON, nullable=True)                     # {"erro": str, "etapa": str, "ts": str}
    criado_em = Column(DateTime, default=datetime.utcnow)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    senha_hash = Column(String, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    ativo = Column(String, default="1")