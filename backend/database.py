from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# Cria o arquivo editmind.db na pasta backend
SQLALCHEMY_DATABASE_URL = "sqlite:///./editmind.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# A "Tabela" que vai guardar a memória da IA
class VideoProcessado(Base):
    __tablename__ = "videos_processados"
    id = Column(String, primary_key=True, index=True)
    nome_original = Column(String)
    caminho_video = Column(String)
    caminho_audio = Column(String)
    transcricao = Column(Text)