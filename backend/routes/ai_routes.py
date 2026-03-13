from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os

# Importando os motores (O cérebro do EditMind)
from services import whisper_service
from services import llm_service
from services import ffmpeg_service

router = APIRouter()

# Caminhos que você já definiu no codebase
DIRETORIO_VIDEOS = "uploads/videos"
DIRETORIO_AUDIOS = "uploads/audios"

class PedidoProcessamento(BaseModel):
    id_video: str  # Ex: "yt_12345" ou o UUID do upload

@router.post("/api/ai/processar")
async def processar_inteligencia_video(pedido: PedidoProcessamento, background_tasks: BackgroundTasks):
    # 1. Localiza o vídeo no seu sistema
    # Procuramos por .mp4 ou a extensão original salva
    caminho_video = os.path.join(DIRETORIO_VIDEOS, f"{pedido.id_video}.mp4")
    
    if not os.path.exists(caminho_video):
        # Tenta localizar sem o .mp4 caso o nome já venha completo
        caminho_video = os.path.join(DIRETORIO_VIDEOS, pedido.id_video)
        if not os.path.exists(caminho_video):
            raise HTTPException(status_code=404, detail="Vídeo não encontrado para análise.")

    try:
        # 2. Extração do Áudio (O Whisper precisa do MP3/WAV)
        print(f"[AI] Extraindo áudio de: {pedido.id_video}")
        nome_audio = ffmpeg_service.extrair_audio_para_ia(caminho_video, pedido.id_video)
        caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)

        # 3. Transcrição (Motor Whisper)
        print(f"[AI] Transcrevendo com Whisper...")
        texto_transcrito = whisper_service.transcrever_audio(caminho_audio)

        # 4. Inteligência de Corte (Motor LLM/Llama)
        print(f"[AI] Analisando melhores momentos...")
        corte_sugerido = llm_service.sugerir_cortes(texto_transcrito)

        # 5. Limpeza de rastro (Remove o áudio extraído após o uso)
        background_tasks.add_task(os.remove, caminho_audio)

        return {
            "id": pedido.id_video,
            "status": "sucesso",
            "transcricao": texto_transcrito,
            "corte_sugerido": corte_sugerido
        }

    except Exception as e:
        print(f"[ERRO CRÍTICO IA]: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno no motor de IA.")