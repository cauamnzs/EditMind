from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel
from fastapi.responses import FileResponse
import shutil
import os
import uuid

# ---> IMPORTANDO O BANCO DE DADOS AQUI <---
from database import SessionLocal, VideoProcessado

# Importando os serviços
from services import ffmpeg_service
from services import youtube_service
from services import whisper_service
from services import llm_service

router = APIRouter()

DIRETORIO_VIDEOS = "uploads/videos"
DIRETORIO_AUDIOS = "uploads/audios"

# --- ROTA 1: UPLOAD LOCAL (Mantém a IA ligada e Salva no Banco) ---
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

    # Aqui a IA continua trabalhando porque é a análise principal
    metadados = ffmpeg_service.extrair_metadados_video(caminho_final_video)
    nome_audio = ffmpeg_service.extrair_audio_para_ia(caminho_final_video, id_unico)
    
    caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
    texto_transcrito = whisper_service.transcrever_audio(caminho_audio)
    corte_sugerido = llm_service.sugerir_cortes(texto_transcrito)

    # ==========================================
    # SALVANDO NO BANCO DE DADOS INVISIVELMENTE
    # ==========================================
    db = SessionLocal()
    try:
        novo_projeto = VideoProcessado(
            id=id_unico,
            nome_original=arquivo.filename,
            caminho_video=caminho_final_video,
            caminho_audio=caminho_audio,
            transcricao=texto_transcrito
        )
        db.add(novo_projeto)
        db.commit()
    finally:
        db.close() # Sempre fecha a conexão para liberar a memória

    # O retorno continua intacto pra não quebrar o seu Front-end
    return {
        "sucesso": True,
        "detalhes_tecnicos": metadados,
        "transcricao": texto_transcrito,
        "corte_sugerido": corte_sugerido
    }

# --- ROTA 2: YT DOWNLOADER (Foco em Velocidade - Sem IA e Sem Banco) ---
class DadosYoutube(BaseModel):
    url: str

@router.post("/api/download-youtube")
async def baixar_video_youtube(dados: DadosYoutube, background_tasks: BackgroundTasks): 
    # Validação básica de link
    if not any(x in dados.url for x in ["youtube.com", "youtu.be"]):
         raise HTTPException(status_code=400, detail="Link do YouTube inválido.")

    id_unico = str(uuid.uuid4())
    nome_seguro_video = f"yt_{id_unico}.mp4"
    caminho_final_video = os.path.join(DIRETORIO_VIDEOS, nome_seguro_video)

    try:
        # 1. Executa apenas o download (rápido)
        youtube_service.baixar_video(dados.url, caminho_final_video)

        # 2. Verifica se o arquivo realmente existe antes de enviar
        if not os.path.exists(caminho_final_video):
            raise HTTPException(status_code=500, detail="Erro ao processar arquivo no servidor.")

        # 3. AGENDA A LIMPEZA (Lixeiro automático)
        # O FastAPI vai enviar o arquivo e DEPOIS deletar do seu HD
        background_tasks.add_task(os.remove, caminho_final_video)

        # 4. DEVOLVE O ARQUIVO IMEDIATAMENTE (Sem Whisper, sem delay)
        return FileResponse(
            path=caminho_final_video,
            media_type="video/mp4",
            filename="Video_EditMind.mp4"
        )
        
    except Exception as e:
        # Se der erro, tenta limpar o rastro se o arquivo foi criado
        if os.path.exists(caminho_final_video):
            os.remove(caminho_final_video)
        print(f"Erro Fatal no Downloader: {str(e)}")
        raise HTTPException(status_code=500, detail="Não foi possível baixar este vídeo. Tente outro link.")
    
@router.get("/api/projetos")
async def listar_projetos():
    """
    Rota para a apresentação: 
    Puxa tudo do banco e mostra de um jeito fácil.
    """
    db = SessionLocal()
    try:
        # Busca todos os vídeos processados
        projetos = db.query(VideoProcessado).all()
        
        # Formata para o JSON ficar limpo
        resultado = []
        for p in projetos:
            resultado.append({
                "id": p.id,
                "video_nome": p.nome_original,
                "transcricao_curta": p.transcricao[:100] + "..." if p.transcricao else "",
                "status": "Finalizado ✅"
            })
            
        return {
            "total": len(resultado),
            "projetos": resultado
        }
    finally:
        db.close()


# --- ROTA 3: PROCESSAR DIRETO DO YOUTUBE ---
@router.post("/api/processar-youtube")
async def analisar_video_youtube_direto(dados: DadosYoutube): 
    print(f"🔗 [API] Recebido pedido YT para: {dados.url}")
    if not any(x in dados.url for x in ["youtube.com", "youtu.be"]):
         raise HTTPException(status_code=400, detail="Link do YouTube inválido.")

    id_unico = str(uuid.uuid4())
    nome_seguro_video = f"yt_{id_unico}.mp4"
    caminho_final_video = os.path.join(DIRETORIO_VIDEOS, nome_seguro_video)

    try:
        # 1. Faz o download direto pra pasta do servidor (rápido)
        youtube_service.baixar_video(dados.url, caminho_final_video)

        if not os.path.exists(caminho_final_video):
            raise HTTPException(status_code=500, detail="Falha no Download do YouTube.")

        # 2. IA Engine entra em ação
        metadados = ffmpeg_service.extrair_metadados_video(caminho_final_video)
        nome_audio = ffmpeg_service.extrair_audio_para_ia(caminho_final_video, id_unico)
        
        caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
        texto_transcrito = whisper_service.transcrever_audio(caminho_audio)
        corte_sugerido = llm_service.sugerir_cortes(texto_transcrito)

        # 3. Salva a memória no Banco de Dados
        db = SessionLocal()
        try:
            novo_projeto = VideoProcessado(
                id=id_unico,
                nome_original=f"YouTube_{id_unico}",
                caminho_video=caminho_final_video,
                caminho_audio=caminho_audio,
                transcricao=texto_transcrito
            )
            db.add(novo_projeto)
            db.commit()
        finally:
            db.close()

        # 4. Devolve o resultado pro Front-end acender a tela
        return {
            "sucesso": True,
            "detalhes_tecnicos": metadados,
            "transcricao": texto_transcrito,
            "corte_sugerido": corte_sugerido
        }
        
    except Exception as e:
        print(f"❌ [Erro Processamento YT]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))