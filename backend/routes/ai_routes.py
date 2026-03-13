from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os

# Importando o Banco de Dados para salvar a memória
from database import SessionLocal, VideoProcessado

# Importando os motores (O cérebro do EditMind)
from services import whisper_service
from services import llm_service
from services import ffmpeg_service

router = APIRouter()

DIRETORIO_VIDEOS = "uploads/videos"
DIRETORIO_AUDIOS = "uploads/audios"

class PedidoProcessamento(BaseModel):
    id_video: str  # Ex: "yt_12345" ou o UUID do arquivo

@router.post("/api/ai/processar")
async def processar_inteligencia_video(pedido: PedidoProcessamento, background_tasks: BackgroundTasks):
    """
    Rota para processar um vídeo que JÁ ESTÁ na pasta do servidor.
    Útil para reprocessamento ou processamento em lote (batch).
    """
    # 1. Localiza o vídeo no HD
    caminho_video = os.path.join(DIRETORIO_VIDEOS, f"{pedido.id_video}.mp4")
    
    if not os.path.exists(caminho_video):
        # Tenta localizar sem o .mp4 caso o nome já venha completo
        caminho_video = os.path.join(DIRETORIO_VIDEOS, pedido.id_video)
        if not os.path.exists(caminho_video):
            raise HTTPException(status_code=404, detail="Vídeo não encontrado para análise no servidor.")

    try:
        # 2. Extração do Áudio 
        print(f"🎬 [AI Route] Extraindo áudio do arquivo: {pedido.id_video}")
        nome_audio = ffmpeg_service.extrair_audio_para_ia(caminho_video, pedido.id_video)
        caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)

        # 3. Transcrição (Motor Whisper na RTX 4060)
        print(f"🦻 [AI Route] Ouvindo o vídeo com Whisper...")
        texto_transcrito = whisper_service.transcrever_audio(caminho_audio)

        # 4. Inteligência de Corte (Motor OpenRouter/Gemini)
        print(f"🧠 [AI Route] Procurando clímax viral...")
        corte_sugerido = llm_service.sugerir_cortes(texto_transcrito)

        # 5. SALVANDO / ATUALIZANDO O BANCO DE DADOS
        db = SessionLocal()
        try:
            # Verifica se já existe no banco para não duplicar
            projeto_existente = db.query(VideoProcessado).filter(VideoProcessado.id == pedido.id_video).first()
            
            if projeto_existente:
                # Atualiza a transcrição se já existir
                projeto_existente.transcricao = texto_transcrito
            else:
                # Cria um novo registro se não existir
                novo_projeto = VideoProcessado(
                    id=pedido.id_video,
                    nome_original=pedido.id_video,
                    caminho_video=caminho_video,
                    caminho_audio=caminho_audio,
                    transcricao=texto_transcrito
                )
                db.add(novo_projeto)
            
            db.commit()
        finally:
            db.close()

        # 6. Limpeza de rastro (Remove o .mp3 para não lotar o HD)
        background_tasks.add_task(os.remove, caminho_audio)

        # 7. Retorno formatado para o Front-end
        return {
            "sucesso": True,
            "id": pedido.id_video,
            "transcricao": texto_transcrito,
            "corte_sugerido": corte_sugerido
        }

    except Exception as e:
        print(f"❌ [ERRO CRÍTICO AI ROUTE]: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno no motor de IA durante o processamento.")