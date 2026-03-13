from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks # <-- 1. Adicionado o BackgroundTasks aqui
from pydantic import BaseModel
from fastapi.responses import FileResponse
import shutil
import os
import uuid

# Importando TODOS os nossos serviços (A Cozinha)
from services import ffmpeg_service
from services import youtube_service
from services import whisper_service
from services import llm_service

router = APIRouter()

DIRETORIO_VIDEOS = "uploads/videos"
DIRETORIO_AUDIOS = "uploads/audios"

@router.post("/api/upload")
async def receber_video_upload(arquivo: UploadFile = File(...)):
    if not arquivo.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Formato inválido.")

    extensao_arquivo = arquivo.filename.split(".")[-1]
    id_unico = str(uuid.uuid4())
    nome_seguro_video = f"{id_unico}.{extensao_arquivo}"
    caminho_final_video = os.path.join(DIRETORIO_VIDEOS, nome_seguro_video)

    try:
        with open(caminho_final_video, "wb") as espaco_memoria:
            shutil.copyfileobj(arquivo.file, espaco_memoria)
    except Exception as erro_sistema:
        raise HTTPException(status_code=500, detail=str(erro_sistema))
    finally:
        arquivo.file.close()

    # Delegando as tarefas para os Services
    tamanho_mb = round(os.path.getsize(caminho_final_video) / (1024 * 1024), 2)
    metadados = ffmpeg_service.extrair_metadados_video(caminho_final_video)
    nome_audio = ffmpeg_service.extrair_audio_para_ia(caminho_final_video, id_unico)

    # Motor da IA
    caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
    texto_transcrito = whisper_service.transcrever_audio(caminho_audio)
    corte_sugerido = llm_service.sugerir_cortes(texto_transcrito)

    return {
        "sucesso": True,
        "video_salvo": nome_seguro_video,
        "tamanho_mb": tamanho_mb,
        "detalhes_tecnicos": metadados,
        "transcricao": texto_transcrito,
        "corte_sugerido": corte_sugerido
    }

class DadosYoutube(BaseModel):
    url: str

# 2. Adicionado o background_tasks na assinatura da função
@router.post("/api/download-youtube")
async def baixar_video_youtube(dados: DadosYoutube, background_tasks: BackgroundTasks): 
    if not "youtube.com" in dados.url and not "youtu.be" in dados.url:
         raise HTTPException(status_code=400, detail="Link inválido.")

    id_unico = str(uuid.uuid4())
    nome_seguro_video = f"yt_{id_unico}.mp4"
    caminho_final_video = os.path.join(DIRETORIO_VIDEOS, nome_seguro_video)

    try:
        # Chama o serviço do YouTube
        youtube_service.baixar_video(dados.url, caminho_final_video)

        tamanho_mb = round(os.path.getsize(caminho_final_video) / (1024 * 1024), 2)
        metadados = ffmpeg_service.extrair_metadados_video(caminho_final_video)
        nome_audio = ffmpeg_service.extrair_audio_para_ia(caminho_final_video, f"yt_{id_unico}")

        # Motor da IA
        caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
        texto_transcrito = whisper_service.transcrever_audio(caminho_audio)
        corte_sugerido = llm_service.sugerir_cortes(texto_transcrito)

        # --- O PULO DO GATO: LIXEIRO AUTOMÁTICO ---
        # Assim que o arquivo terminar de viajar pelo Ngrok até a casa do Matheus,
        # o FastAPI apaga os arquivos do seu computador automaticamente!
        background_tasks.add_task(os.remove, caminho_final_video)
        background_tasks.add_task(os.remove, caminho_audio)

        # Retorna o arquivo de vídeo usando FileResponse
        return FileResponse(
            path=caminho_final_video,
            media_type="video/mp4",
            filename="Video_EditMind.mp4"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))