from sqlalchemy import create_engine, Column, String, Text, DateTime
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
    # PostgreSQL / MySQL: connection pooling completo
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,              # Conexões mantidas abertas
        max_overflow=20,           # Conexões extras sob demanda
        pool_timeout=30,           # Timeout aguardando conexão
        pool_recycle=1800,         # Recicla conexões a cada 30min
        echo=False
    )

print(f"🗄️  [Database] Engine iniciado: {'SQLite (local)' if _is_sqlite else 'PostgreSQL (produção)'}")

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
    criado_em = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, nullable=True)  # Para futuro multi-tenant

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    senha_hash = Column(String, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    ativo = Column(String, default="1")