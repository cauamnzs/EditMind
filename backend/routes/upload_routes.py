from fastapi import APIRouter, File, Form, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import uuid
import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

# ---> IMPORTANDO O BANCO DE DADOS OTIMIZADO <---
from database import get_db_session, VideoProcessado, get_db
from sqlalchemy.orm import Session

# Importando os serviços
from services import ffmpeg_service
from services import youtube_service
from services import whisper_service
from services import llm_service
from routes.sse_routes import criar_fila_sse, emitir_evento

log = logging.getLogger("editmind.upload")

router = APIRouter()

DIRETORIO_VIDEOS = "uploads/videos"
DIRETORIO_AUDIOS = "uploads/audios"
DIRETORIO_CORTES = "uploads/cortes"

# ==========================================
# POOL DE EXECUTORES PARA OPERAÇÕES BLOQUEANTES
# ==========================================
# Limita concorrência de processamento pesado (Whisper/FFmpeg)
_process_executor = ThreadPoolExecutor(max_workers=3)

# Diretórios de temp para cleanup
_TEMP_DIRS = ["uploads/temp_clips", "uploads/broll"]
_TEMP_MAX_AGE_S = 3600  # 1 hora


def _cleanup_temp_files() -> None:
    """Remove arquivos de temp com mais de _TEMP_MAX_AGE_S segundos."""
    agora = time.time()
    removidos = 0
    for diretorio in _TEMP_DIRS:
        if not os.path.isdir(diretorio):
            continue
        for nome in os.listdir(diretorio):
            caminho = os.path.join(diretorio, nome)
            try:
                if os.path.isfile(caminho) and (agora - os.path.getmtime(caminho)) > _TEMP_MAX_AGE_S:
                    os.remove(caminho)
                    removidos += 1
            except OSError:
                pass
    if removidos:
        log.info("[Cleanup] %d arquivo(s) temporário(s) removido(s)", removidos)


# --- ROTA 1: UPLOAD LOCAL (Otimizada com Async e Context Manager) ---
@router.post("/api/upload")
async def receber_video_upload(
    background_tasks: BackgroundTasks,
    arquivo: UploadFile = File(...),
    tempo_alvo: int = Form(default=60, alias="tempo_corte"),
    id_video_hint: Optional[str] = Form(None),
):
    if not arquivo.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Formato inválido. Apenas vídeos.")

    extensao_arquivo = arquivo.filename.split(".")[-1]
    # Usa hint do frontend para permitir SSE pré-conectado
    id_unico = id_video_hint if id_video_hint and len(id_video_hint) < 80 else str(uuid.uuid4())
    nome_seguro_video = f"{id_unico}.{extensao_arquivo}"
    caminho_final_video = os.path.join(DIRETORIO_VIDEOS, nome_seguro_video)

    t0 = time.time()
    # Cria fila SSE para este upload (cliente já deve estar ouvindo)
    criar_fila_sse(id_unico)

    # 1. Lê e salva o arquivo
    try:
        conteudo = await arquivo.read()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_process_executor, _salvar_bytes_sync, conteudo, caminho_final_video)
    except Exception as e:
        await emitir_evento(id_unico, "erro", f"Falha ao salvar arquivo: {e}", 0)
        raise HTTPException(status_code=500, detail=f"Erro salvando arquivo: {e}")

    # 2. Metadados
    try:
        loop = asyncio.get_running_loop()
        metadados = await loop.run_in_executor(_process_executor, ffmpeg_service.extrair_metadados_video, caminho_final_video)
        metadados["video_url"] = f"/uploads/videos/{nome_seguro_video}"
        metadados["id_video"] = id_unico
        metadados["caminho"] = caminho_final_video
    except Exception as e:
        await emitir_evento(id_unico, "erro", f"Falha nos metadados: {e}", 0)
        raise HTTPException(status_code=500, detail=f"Erro metadados: {e}")

    duracao_video = float(metadados.get("duracao_segundos", 0))

    # Registra projeto no banco como "processando"
    try:
        with get_db_session() as db:
            novo_projeto = VideoProcessado(
                id=id_unico,
                nome_original=arquivo.filename,
                caminho_video=caminho_final_video,
                caminho_audio="",
                transcricao="",
                status="processando",
                duracao_segundos=duracao_video,
            )
            db.add(novo_projeto)
    except Exception as e:
        log.warning("[DB] Falha ao criar registro inicial: %s", e)

    # 3. Pipeline IA com SSE
    try:
        resultado_ia = await _processar_ia_async(caminho_final_video, id_unico, tempo_alvo)
        texto_transcrito = resultado_ia["transcricao"]
        corte_sugerido = resultado_ia["corte_sugerido"]
        caminho_audio = resultado_ia["caminho_audio"]
    except Exception as e:
        await emitir_evento(id_unico, "erro", f"Pipeline IA falhou: {e}", 0)
        with get_db_session() as db:
            p = db.query(VideoProcessado).filter(VideoProcessado.id == id_unico).first()
            if p:
                p.status = "erro"
                p.export_log = {"erro": str(e), "etapa": "pipeline_ia", "ts": datetime.now(timezone.utc).isoformat()}
        raise HTTPException(status_code=500, detail=f"Erro no processamento IA: {e}")

    # 4. Atualiza banco com resultado completo
    try:
        with get_db_session() as db:
            p = db.query(VideoProcessado).filter(VideoProcessado.id == id_unico).first()
            if p:
                p.transcricao = texto_transcrito
                p.caminho_audio = caminho_audio
                p.metadados_edicao = corte_sugerido if isinstance(corte_sugerido, list) else None
                p.status = "pronto"
                p.duracao_segundos = duracao_video
        log.info("[DB] Projeto %s salvo — %d cortes — %.1fs total",
                 id_unico, len(corte_sugerido) if isinstance(corte_sugerido, list) else 0, time.time() - t0)
    except Exception as e:
        log.warning("[DB] Erro atualizando projeto: %s", e)

    # 5. Cleanup agendado
    background_tasks.add_task(_cleanup_temp_files)

    await emitir_evento(id_unico, "concluido", "Pipeline concluído com sucesso", 100, {
        "id_video": id_unico,
        "n_cortes": len(corte_sugerido) if isinstance(corte_sugerido, list) else 0,
    })

    return {
        "sucesso": True,
        "detalhes_tecnicos": metadados,
        "transcricao": texto_transcrito,
        "corte_sugerido": corte_sugerido,
        "id_video": id_unico,
    }

def _salvar_arquivo_sync(arquivo: UploadFile, caminho: str):
    """Função síncrona para salvar arquivo (executada em thread)."""
    try:
        with open(caminho, "wb") as f:
            shutil.copyfileobj(arquivo.file, f)
    finally:
        arquivo.file.close()

def _salvar_bytes_sync(conteudo: bytes, caminho: str):
    """Função síncrona para salvar bytes em arquivo (executada em thread)."""
    with open(caminho, "wb") as f:
        f.write(conteudo)

async def _processar_ia_async(caminho_video: str, id_unico: str, tempo_alvo: int = 60) -> dict:
    """
    Pipeline IA com eventos SSE por etapa.
    Emite: audio_extraido(20%) → transcricao(50%) → analise_ia(85%) → concluido(100%)
    """
    loop = asyncio.get_running_loop()
    t0 = time.time()

    # ETAPA 1 — Extração de áudio
    await emitir_evento(id_unico, "audio_extraindo", "Extraindo áudio em alta fidelidade...", 15)
    try:
        nome_audio = await loop.run_in_executor(
            _process_executor, ffmpeg_service.extrair_audio_para_ia, caminho_video, id_unico
        )
        if not nome_audio:
            raise RuntimeError("FFmpeg não gerou arquivo de áudio")
    except Exception as e:
        raise RuntimeError(f"Extração de áudio falhou: {e}") from e

    caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
    await emitir_evento(id_unico, "audio_extraido", "Áudio extraído — iniciando Whisper...", 20)
    log.info("[Pipeline:%s] Áudio extraído em %.1fs", id_unico, time.time() - t0)

    # ETAPA 2 — Transcrição Whisper
    await emitir_evento(id_unico, "transcricao", "Whisper transcrevendo com timestamps word-level...", 30)
    try:
        t1 = time.time()
        texto_transcrito, segmentos_whisper = await loop.run_in_executor(
            _process_executor, whisper_service.transcrever_com_timestamps, caminho_audio
        )
        log.info("[Pipeline:%s] Whisper concluído em %.1fs — %d segmentos",
                 id_unico, time.time() - t1, len(segmentos_whisper))
    except Exception as e:
        raise RuntimeError(f"Whisper falhou: {e}") from e

    await emitir_evento(id_unico, "transcricao_ok", f"Transcrição concluída — {len(segmentos_whisper)} segmentos", 55)

    # Duração do vídeo para calibrar n_cortes
    try:
        meta = ffmpeg_service.extrair_metadados_video(caminho_video)
        duracao_total = float(meta.get("duracao_segundos", 0))
    except Exception:
        duracao_total = 0.0

    # ETAPA 3 — Análise LLM
    await emitir_evento(id_unico, "analise_ia", "Brain Engine v2 identificando ganchos virais...", 60)
    try:
        t2 = time.time()
        corte_sugerido = await loop.run_in_executor(
            _process_executor, llm_service.analisar_cortes_virais, segmentos_whisper, duracao_total, tempo_alvo
        )
        log.info("[Pipeline:%s] LLM retornou %d cortes em %.1fs",
                 id_unico, len(corte_sugerido), time.time() - t2)
    except Exception as e:
        log.warning("[Pipeline:%s] Brain Engine v2 falhou: %s", id_unico, e)
        corte_sugerido = []

    # Fallback para prompt legado
    if not corte_sugerido:
        await emitir_evento(id_unico, "analise_ia", "Fallback para Brain Engine v1...", 70)
        try:
            corte_sugerido = await loop.run_in_executor(
                _process_executor, llm_service.sugerir_cortes, texto_transcrito
            )
        except Exception as e:
            log.warning("[Pipeline:%s] Brain Engine v1 também falhou: %s", id_unico, e)
            corte_sugerido = []

    await emitir_evento(
        id_unico, "analise_ok",
        f"{len(corte_sugerido)} cortes virais identificados", 90,
        {"n_cortes": len(corte_sugerido)}
    )
    log.info("[Pipeline:%s] Total pipeline IA: %.1fs", id_unico, time.time() - t0)

    return {
        "transcricao": texto_transcrito,
        "segmentos_whisper": segmentos_whisper,
        "corte_sugerido": corte_sugerido,
        "caminho_audio": caminho_audio,
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
        if os.path.exists(caminho_final_video):
            os.remove(caminho_final_video)
        log.error("[YT Downloader] %s", e)
        raise HTTPException(status_code=500, detail="Não foi possível baixar este vídeo. Tente outro link.")


@router.get("/api/projetos")
async def listar_projetos():
    """Lista projetos do banco com status real, duração e contagem de clips."""
    try:
        from database import ClipGerado
        with get_db_session() as db:
            projetos = db.query(VideoProcessado).order_by(VideoProcessado.criado_em.desc()).all()
            resultado = []
            for p in projetos:
                n_clips = db.query(ClipGerado).filter(ClipGerado.video_id == p.id).count()
                resultado.append({
                    "id": p.id,
                    "video_nome": p.nome_original,
                    "transcricao_curta": (p.transcricao or "")[:100] + ("..." if p.transcricao and len(p.transcricao) > 100 else ""),
                    "status": p.status or "pronto",
                    "duracao_segundos": p.duracao_segundos,
                    "n_clips": n_clips,
                    "video_url": f"/uploads/videos/{p.id}.mp4",
                    "criado_em": p.criado_em.isoformat() if p.criado_em else None,
                })
            return {"total": len(resultado), "projetos": resultado}
    except Exception as e:
        log.error("[DB] listar_projetos: %s", e)
        return {"total": 0, "projetos": [], "erro": str(e)}

# --- ROTA 3: PROCESSAR DIRETO DO YOUTUBE ---
@router.post("/api/processar-youtube")
async def analisar_video_youtube_direto(dados: DadosYoutube): 
    log.info("[YT] Processando: %s", dados.url)
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

        # 3. Salva a memória no Banco de Dados usando context manager
        try:
            with get_db_session() as db:
                novo_projeto = VideoProcessado(
                    id=id_unico,
                    nome_original=f"YouTube_{id_unico}",
                    caminho_video=caminho_final_video,
                    caminho_audio=caminho_audio,
                    transcricao=texto_transcrito
                )
                db.add(novo_projeto)
        except Exception as e:
            print(f"⚠️ [DB Warning] Erro salvando YouTube: {e}")

        # 4. Devolve o resultado pro Front-end acender a tela
        metadados["video_url"] = f"/uploads/videos/{nome_seguro_video}"
        metadados["id_video"] = id_unico
        metadados["caminho"] = caminho_final_video
        
        return {
            "sucesso": True,
            "detalhes_tecnicos": metadados,
            "transcricao": texto_transcrito,
            "corte_sugerido": corte_sugerido,
            "id_video": id_unico
        }
        
    except Exception as e:
        print(f"❌ [Erro Processamento YT]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))