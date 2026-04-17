from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import uuid
import asyncio
import time
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger("editmind.ai")

# Importando o Banco de Dados otimizado
from database import get_db_session, VideoProcessado, ClipGerado

# Importando os motores
from services import whisper_service
from services import llm_service
from services import ffmpeg_service
from services import pexels_service

router = APIRouter()

DIRETORIO_VIDEOS = "uploads/videos"
DIRETORIO_AUDIOS = "uploads/audios"
DIRETORIO_CORTES = "uploads/cortes"
os.makedirs(DIRETORIO_CORTES, exist_ok=True)

# Executor para operações pesadas FFmpeg
_ffmpeg_executor = ThreadPoolExecutor(max_workers=2)

class PedidoProcessamento(BaseModel):
    id_video: str
    headline: Optional[str] = None
    focus_x: Optional[int] = Field(default=50, ge=0, le=100)  # 0-100 para posição crop
    jump_cut: Optional[bool] = False

class GerarCorteRequest(BaseModel):
    id_video: str
    inicio: str  # "00:10" ou segundos
    fim: str
    headline: Optional[str] = None
    focus_x: Optional[int] = 50
    texto_legendas: Optional[str] = None
    jump_cut: Optional[bool] = False  # Ativa remoção de silêncios
    usar_broll: Optional[bool] = False  # Ativa overlay de imagem B-Roll
    keyword_broll: Optional[str] = None  # Palavra-chave para busca (opcional)

@router.post("/api/ai/processar")
async def processar_inteligencia_video(pedido: PedidoProcessamento, background_tasks: BackgroundTasks):
    """
    Reprocessa um vídeo já existente no servidor.
    Async com ThreadPool para não bloquear.
    """
    # Localiza vídeo
    caminho_video = os.path.join(DIRETORIO_VIDEOS, f"{pedido.id_video}.mp4")
    if not os.path.exists(caminho_video):
        caminho_video = os.path.join(DIRETORIO_VIDEOS, pedido.id_video)
        if not os.path.exists(caminho_video):
            raise HTTPException(status_code=404, detail="Vídeo não encontrado.")

    try:
        loop = asyncio.get_running_loop()
        
        # Extrai áudio em thread
        nome_audio = await loop.run_in_executor(
            _ffmpeg_executor,
            ffmpeg_service.extrair_audio_para_ia,
            caminho_video,
            pedido.id_video
        )
        caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)

        # Transcreve
        texto_transcrito = await loop.run_in_executor(
            _ffmpeg_executor,
            whisper_service.transcrever_audio,
            caminho_audio
        )

        # Análise LLM
        corte_sugerido = await loop.run_in_executor(
            _ffmpeg_executor,
            llm_service.sugerir_cortes,
            texto_transcrito
        )

        # Salva no banco
        with get_db_session() as db:
            projeto = db.query(VideoProcessado).filter(VideoProcessado.id == pedido.id_video).first()
            if projeto:
                projeto.transcricao = texto_transcrito
            else:
                novo = VideoProcessado(
                    id=pedido.id_video,
                    nome_original=pedido.id_video,
                    caminho_video=caminho_video,
                    caminho_audio=caminho_audio,
                    transcricao=texto_transcrito
                )
                db.add(novo)

        # Limpa áudio em background
        background_tasks.add_task(os.remove, caminho_audio)

        return {
            "sucesso": True,
            "id": pedido.id_video,
            "transcricao": texto_transcrito,
            "corte_sugerido": corte_sugerido
        }

    except Exception as e:
        print(f"❌ [AI Route Error]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")


# ==========================================
# ROTAS PARA VISUALIZAÇÃO E DOWNLOAD
# ==========================================

@router.get("/api/video/{video_id}")
async def stream_video(video_id: str):
    """Stream do vídeo original para o player."""
    caminho = os.path.join(DIRETORIO_VIDEOS, f"{video_id}.mp4")
    if not os.path.exists(caminho):
        # Tenta encontrar com extensão variada
        for ext in [".mp4", ".mov", ".avi", ".mkv"]:
            caminho = os.path.join(DIRETORIO_VIDEOS, f"{video_id}{ext}")
            if os.path.exists(caminho):
                break
        else:
            raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    
    return FileResponse(
        path=caminho,
        media_type="video/mp4",
        filename=f"{video_id}.mp4"
    )

@router.post("/api/ai/gerar-corte")
async def gerar_corte_video(req: GerarCorteRequest, background_tasks: BackgroundTasks):
    """
    Gera um corte vertical 9:16 com:
    - Headline opcional (drawtext)
    - Smart Focus (crop posicionável)
    - Jump Cut (remoção de silêncios)
    - B-Roll (overlay de imagem)
    
    Retorna URL para download do arquivo gerado.
    """
    caminho_video = os.path.join(DIRETORIO_VIDEOS, f"{req.id_video}.mp4")
    if not os.path.exists(caminho_video):
        raise HTTPException(status_code=404, detail="Vídeo fonte não encontrado")
    
    # Converte timestamps
    def ts_para_seg(ts: str) -> float:
        if ":" in ts:
            partes = ts.split(":")
            if len(partes) == 2:
                return int(partes[0]) * 60 + float(partes[1])
            elif len(partes) == 3:
                return int(partes[0]) * 3600 + int(partes[1]) * 60 + float(partes[2])
        return float(ts)
    
    inicio_seg = ts_para_seg(req.inicio)
    fim_seg = ts_para_seg(req.fim)
    duracao = fim_seg - inicio_seg
    
    if duracao <= 0 or duracao > 300:  # Max 5 minutos
        raise HTTPException(status_code=400, detail="Duração inválida (max 5min)")
    
    # Nome do arquivo de saída
    output_id = f"{req.id_video}_{int(inicio_seg)}_{int(fim_seg)}"
    caminho_saida = os.path.join(DIRETORIO_CORTES, f"{output_id}.mp4")
    caminho_temp = os.path.join(DIRETORIO_CORTES, f"{output_id}_temp.mp4")
    
    try:
        loop = asyncio.get_running_loop()
        
        # ==========================================
        # FASE 2: JUMP CUT (Remoção de silêncios)
        # ==========================================
        silencios = []
        if req.jump_cut:
            print(f"⚡ [Jump Cut] Ativado para corte {req.inicio}-{req.fim}")
            
            # Extrai áudio do trecho para análise
            nome_audio = await loop.run_in_executor(
                _ffmpeg_executor,
                ffmpeg_service.extrair_audio_para_ia,
                caminho_video,
                f"jump_{output_id}"
            )
            caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
            
            # Transcreve com timestamps para detectar silêncios
            _, segmentos = await loop.run_in_executor(
                _ffmpeg_executor,
                whisper_service.transcrever_com_timestamps,
                caminho_audio
            )
            
            # Extrai silêncios
            silencios = whisper_service.extrair_momentos_sem_fala(segmentos, min_silence_sec=0.5)
            print(f"🔇 [Jump Cut] {len(silencios)} silêncios detectados")
            
            # Limpa áudio temporário
            background_tasks.add_task(os.remove, caminho_audio)
        
        # ==========================================
        # FASE 1/2: GERA CORTE BASE (com ou sem Jump Cut)
        # ==========================================
        if req.jump_cut and silencios:
            # Usa função de Jump Cut que remove silêncios
            await loop.run_in_executor(
                _ffmpeg_executor,
                ffmpeg_service.gerar_jump_cut,
                caminho_video,
                caminho_temp,
                inicio_seg,
                fim_seg,
                silencios,
                req.focus_x
            )
        else:
            # Corte normal vertical
            await loop.run_in_executor(
                _ffmpeg_executor,
                ffmpeg_service.gerar_corte_vertical,
                caminho_video,
                caminho_temp,
                inicio_seg,
                duracao,
                None,  # Headline será adicionada depois se necessário
                req.focus_x
            )
        
        # ==========================================
        # FASE 2: B-ROLL (Overlay de imagem)
        # ==========================================
        if req.usar_broll:
            print(f"🎨 [B-Roll] Ativado para corte")
            
            # Determina keyword para busca
            keyword = req.keyword_broll if req.keyword_broll else "abstract"
            
            # Busca imagem no Pexels
            imagem_info = await loop.run_in_executor(
                _ffmpeg_executor,
                pexels_service.buscar_imagem_broll,
                keyword,
                "portrait"
            )
            
            if imagem_info:
                # Baixa imagem para cache
                caminho_imagem = await loop.run_in_executor(
                    _ffmpeg_executor,
                    pexels_service.baixar_imagem_para_cache,
                    imagem_info["url_portrait"] or imagem_info["url_medium"]
                )
                
                if caminho_imagem:
                    # Aplica overlay B-Roll no meio do corte (2s de duração)
                    meio_corte = duracao / 2
                    overlays = [{
                        "imagem": caminho_imagem,
                        "inicio": max(0, meio_corte - 1),
                        "duracao": 2.0
                    }]
                    
                    await loop.run_in_executor(
                        _ffmpeg_executor,
                        ffmpeg_service.adicionar_broll,
                        caminho_temp,
                        caminho_saida,
                        overlays
                    )
                    
                    # Limpa temp
                    background_tasks.add_task(os.remove, caminho_temp)
                else:
                    # Sem imagem, apenas renomeia temp
                    os.rename(caminho_temp, caminho_saida)
            else:
                os.rename(caminho_temp, caminho_saida)
        else:
            # Sem B-Roll, apenas renomeia temp
            if os.path.exists(caminho_temp):
                os.rename(caminho_temp, caminho_saida)
        
        # ==========================================
        # ADICIONA HEADLINE SE NECESSÁRIO (depois de todo processamento)
        # ==========================================
        if req.headline and req.headline.strip():
            caminho_final = os.path.join(DIRETORIO_CORTES, f"{output_id}_final.mp4")
            
            await loop.run_in_executor(
                _ffmpeg_executor,
                ffmpeg_service.adicionar_headline,
                caminho_saida,
                caminho_final,
                req.headline
            )
            
            # Substitui pelo final
            background_tasks.add_task(os.remove, caminho_saida)
            os.rename(caminho_final, caminho_saida)
        
        if not os.path.exists(caminho_saida):
            raise Exception("FFmpeg falhou ao gerar corte")
        
        # Retorna info para o frontend
        return {
            "sucesso": True,
            "corte_id": output_id,
            "video_url": f"/uploads/cortes/{output_id}.mp4",
            "download_url": f"/api/ai/download-corte/{output_id}",
            "duracao": duracao,
            "features": {
                "jump_cut": req.jump_cut,
                "broll": req.usar_broll,
                "headline": bool(req.headline),
                "focus": req.focus_x
            }
        }
        
    except Exception as e:
        print(f"❌ [Gerar Corte Error]: {e}")
        raise HTTPException(status_code=500, detail=f"Erro gerando corte: {str(e)}")

class PreviewCorteRequest(BaseModel):
    id_video: str
    segments_to_keep: Optional[List[dict]] = None  # se None, usa start/end
    start: Optional[float] = 0.0
    end: Optional[float] = 0.0
    focus_x: Optional[int] = Field(default=50, ge=0, le=100)
    synced_transcript: Optional[List[dict]] = None


@router.post("/api/ai/preview-corte")
async def preview_corte(req: PreviewCorteRequest):
    """
    Gera um preview fast do corte usando h264_nvenc (RTX 4060).
    O arquivo resultante começa em 0.0 e fica em uploads/temp_clips/{clip_uuid}.mp4.
    Retorna video_url, vtt_url e duracao_exata para o frontend atualizar o player.
    """
    caminho_video = os.path.join(DIRETORIO_VIDEOS, f"{req.id_video}.mp4")
    if not os.path.exists(caminho_video):
        for ext in [".mov", ".avi", ".mkv", ".webm"]:
            alt = os.path.join(DIRETORIO_VIDEOS, f"{req.id_video}{ext}")
            if os.path.exists(alt):
                caminho_video = alt
                break
        else:
            raise HTTPException(status_code=404, detail="Vídeo fonte não encontrado")

    clip_uuid = f"prev_{req.id_video}_{uuid.uuid4().hex[:8]}"

    try:
        loop = asyncio.get_running_loop()
        caminho_clip, duracao_exata = await loop.run_in_executor(
            _ffmpeg_executor,
            ffmpeg_service.gerar_preview_do_corte,
            caminho_video,
            clip_uuid,
            req.segments_to_keep,
            req.start or 0.0,
            req.end or 0.0,
            req.focus_x,
            (1080, 1920),
            True  # use_nvenc
        )

        if not os.path.exists(caminho_clip):
            raise Exception("Preview não gerado")

        vtt_url = None
        if req.synced_transcript:
            vtt_content = _gerar_vtt_sincronizado(req.synced_transcript)
            vtt_path = caminho_clip.replace(".mp4", ".vtt")
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)
            vtt_url = f"/uploads/temp_clips/{clip_uuid}.vtt"

        return {
            "sucesso": True,
            "clip_uuid": clip_uuid,
            "video_url": f"/uploads/temp_clips/{clip_uuid}.mp4",
            "vtt_url": vtt_url,
            "duracao_exata": round(duracao_exata, 3)
        }

    except Exception as e:
        print(f"❌ [Preview Error]: {e}")
        raise HTTPException(status_code=500, detail=f"Erro gerando preview: {str(e)}")

class GerarCorteViralRequest(BaseModel):
    id_video: str
    segments_to_keep: List[dict]             # [{"start": float, "end": float}]
    synced_transcript: Optional[List[dict]] = None  # [{"start_offset", "end_offset", "text"}]
    headline: Optional[str] = None
    focus_x: Optional[int] = Field(default=50, ge=0, le=100)
    usar_broll: Optional[bool] = False
    keyword_broll: Optional[str] = None
    titulo: Optional[str] = None
    viral_score: Optional[int] = None


@router.post("/api/ai/gerar-corte-viral")
async def gerar_corte_viral(req: GerarCorteViralRequest, background_tasks: BackgroundTasks):
    """
    Pipeline completo do Editor Chefe:
    1. Recebe segments_to_keep (jump-cuts internos) do frontend
    2. Chama concatenar_segmentos para renderizar o clipe definitivo
    3. Aplica B-Roll se solicitado
    4. Retorna URL do vídeo + VTT sincronizado com synced_transcript

    O vídeo resultante NÃO é o bruto — é o clipe final com tempo morto removido.
    """
    if not req.segments_to_keep:
        raise HTTPException(status_code=400, detail="segments_to_keep é obrigatório")

    # Localiza vídeo fonte
    caminho_video = os.path.join(DIRETORIO_VIDEOS, f"{req.id_video}.mp4")
    if not os.path.exists(caminho_video):
        for ext in [".mov", ".avi", ".mkv", ".webm"]:
            alt = os.path.join(DIRETORIO_VIDEOS, f"{req.id_video}{ext}")
            if os.path.exists(alt):
                caminho_video = alt
                break
        else:
            raise HTTPException(status_code=404, detail="Vídeo fonte não encontrado")

    # Gera ID único para o corte baseado nos timestamps
    primeiro = req.segments_to_keep[0]
    ultimo   = req.segments_to_keep[-1]
    output_id    = f"{req.id_video}_viral_{int(float(primeiro['start']))}_{int(float(ultimo['end']))}"
    caminho_saida = os.path.join(DIRETORIO_CORTES, f"{output_id}.mp4")
    caminho_temp  = os.path.join(DIRETORIO_CORTES, f"{output_id}_broll.mp4")

    try:
        loop = asyncio.get_running_loop()

        # ──────────────────────────────────────────
        # ETAPA 1: RENDERIZA JUMP CUTS INTERNOS
        # ──────────────────────────────────────────
        print(f"🎬 [Viral Cut] Renderizando {len(req.segments_to_keep)} segmentos para '{req.titulo}'")

        caminho_saida, duracao_final = await loop.run_in_executor(
            _ffmpeg_executor,
            ffmpeg_service.concatenar_segmentos,
            caminho_video,
            caminho_saida,
            req.segments_to_keep,
            req.focus_x,
            req.headline,
        )

        if not os.path.exists(caminho_saida):
            raise Exception("concatenar_segmentos não gerou arquivo de saída")

        # ──────────────────────────────────────────
        # ETAPA 2: B-ROLL (opcional)
        # ──────────────────────────────────────────
        if req.usar_broll:
            keyword = req.keyword_broll or "abstract"
            imagem_info = await loop.run_in_executor(
                _ffmpeg_executor,
                pexels_service.buscar_imagem_broll,
                keyword,
                "portrait"
            )
            if imagem_info:
                caminho_imagem = await loop.run_in_executor(
                    _ffmpeg_executor,
                    pexels_service.baixar_imagem_para_cache,
                    imagem_info.get("url_portrait") or imagem_info.get("url_medium")
                )
                if caminho_imagem:
                    duracao_editada = sum(
                        float(s["end"]) - float(s["start"]) for s in req.segments_to_keep
                    )
                    meio = duracao_editada / 2
                    overlays = [{"imagem": caminho_imagem, "inicio": max(0, meio - 1), "duracao": 2.0}]
                    
                    await loop.run_in_executor(
                        _ffmpeg_executor,
                        ffmpeg_service.adicionar_broll,
                        caminho_saida,
                        caminho_temp,
                        overlays
                    )
                    
                    background_tasks.add_task(os.remove, caminho_saida)
                    os.rename(caminho_temp, caminho_saida)

        # ──────────────────────────────────────────
        # ETAPA 3: GERA VTT SINCRONIZADO
        # ──────────────────────────────────────────
        vtt_url = None
        if req.synced_transcript:
            vtt_content = _gerar_vtt_sincronizado(req.synced_transcript)
            vtt_filename = f"{output_id}.vtt"
            vtt_path = os.path.join(DIRETORIO_CORTES, vtt_filename)
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)
            vtt_url = f"/uploads/cortes/{vtt_filename}"
            print(f"📄 [VTT] Gerado: {vtt_filename}")

        # duracao_final já vem medida por ffprobe em concatenar_segmentos

        # Persiste ClipGerado no banco para evitar re-processamento
        try:
            with get_db_session() as db:
                clip = ClipGerado(
                    id=output_id,
                    video_id=req.id_video,
                    cut_id=getattr(req, 'cut_id', None),
                    titulo=req.titulo,
                    viral_score=req.viral_score,
                    gancho=None,
                    motivo=None,
                    keyword_broll=req.keyword_broll,
                    raw_start=str(float(req.segments_to_keep[0]["start"])),
                    raw_end=str(float(req.segments_to_keep[-1]["end"])),
                    duracao_editada=round(duracao_final, 2),
                    caminho_clip=os.path.join(DIRETORIO_CORTES, f"{output_id}.mp4"),
                    caminho_vtt=os.path.join(DIRETORIO_CORTES, f"{output_id}.vtt") if vtt_url else None,
                    segments_to_keep=req.segments_to_keep,
                    synced_transcript=req.synced_transcript
                )
                db.add(clip)
            print(f"💾 [DB] ClipGerado salvo: {output_id}")
        except Exception as e:
            print(f"⚠️ [DB] Erro salvando ClipGerado (não crítico): {e}")

        return {
            "sucesso": True,
            "corte_id": output_id,
            "video_url":    f"/uploads/cortes/{output_id}.mp4",
            "download_url": f"/api/ai/download-corte/{output_id}",
            "vtt_url":      vtt_url,
            "duracao_editada": round(duracao_final, 2),
            "segmentos_renderizados": len(req.segments_to_keep),
            "features": {
                "jump_cut_viral": True,
                "broll": req.usar_broll,
                "headline": bool(req.headline),
                "focus": req.focus_x,
                "synced_transcript": bool(req.synced_transcript)
            }
        }

    except Exception as e:
        print(f"❌ [Viral Cut Error]: {e}")
        raise HTTPException(status_code=500, detail=f"Erro gerando corte viral: {str(e)}")


def _gerar_vtt_sincronizado(synced_transcript: List[dict]) -> str:
    """
    Converte synced_transcript do Editor Chefe em arquivo VTT.
    Os offsets já são relativos ao clipe editado (0.0 = início do clipe).
    """
    def fmt(s: float) -> str:
        h  = int(s) // 3600
        m  = (int(s) % 3600) // 60
        ss = int(s) % 60
        ms = int((s % 1) * 1000)
        return f"{h:02d}:{m:02d}:{ss:02d}.{ms:03d}"

    linhas = ["WEBVTT", ""]
    for i, cue in enumerate(synced_transcript, start=1):
        start = float(cue.get("start_offset", 0))
        end   = float(cue.get("end_offset", start + 1.5))
        text  = cue.get("text", "").strip()
        if not text:
            continue
        linhas.append(str(i))
        linhas.append(f"{fmt(start)} --> {fmt(end)}")
        linhas.append(text)
        linhas.append("")

    return "\n".join(linhas)


@router.get("/api/video/{id_video}/clips")
async def listar_clips_do_video(id_video: str):
    """
    Retorna todos os ClipGerados de um vídeo já processado.
    Permite o frontend recarregar cortes sem re-processar Whisper + LLM.
    Também retorna metadados_edicao do vídeo (JSON Editor Chefe v2).
    """
    try:
        with get_db_session() as db:
            video = db.query(VideoProcessado).filter(VideoProcessado.id == id_video).first()
            if not video:
                raise HTTPException(status_code=404, detail="Vídeo não encontrado")

            clips = db.query(ClipGerado).filter(ClipGerado.video_id == id_video).order_by(ClipGerado.criado_em).all()

            clips_list = [
                {
                    "id": c.id,
                    "cut_id": c.cut_id,
                    "titulo": c.titulo,
                    "viral_score": c.viral_score,
                    "keyword_broll": c.keyword_broll,
                    "raw_start": c.raw_start,
                    "raw_end": c.raw_end,
                    "duracao_editada": c.duracao_editada,
                    "video_url": f"/uploads/cortes/{c.id}.mp4" if c.caminho_clip else None,
                    "vtt_url": f"/uploads/cortes/{c.id}.vtt" if c.caminho_vtt else None,
                    "download_url": f"/api/ai/download-corte/{c.id}",
                    "segments_to_keep": c.segments_to_keep,
                    "synced_transcript": c.synced_transcript,
                    "criado_em": c.criado_em.isoformat() if c.criado_em else None
                }
                for c in clips
            ]

            return {
                "id_video": id_video,
                "nome_original": video.nome_original,
                "transcricao": video.transcricao,
                "metadados_edicao": video.metadados_edicao,
                "clips_gerados": clips_list,
                "total_clips": len(clips_list)
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [clips] Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/ai/download-corte/{corte_id}")
async def download_corte(corte_id: str):
    """Download do corte gerado."""
    caminho = os.path.join(DIRETORIO_CORTES, f"{corte_id}.mp4")
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Corte não encontrado")
    
    return FileResponse(
        path=caminho,
        media_type="video/mp4",
        filename=f"EditMind_Corte_{corte_id}.mp4"
    )


# ──────────────────────────────────────────────────────────────────────
# BATCH EXPORT
# ──────────────────────────────────────────────────────────────────────
_batch_semaphore = asyncio.Semaphore(2)  # max 2 renders simultâneos


class BatchExportRequest(BaseModel):
    id_video: str
    cortes: List[dict]              # lista de objetos com campos de GerarCorteViralRequest
    focus_x: Optional[int] = Field(default=50, ge=0, le=100)
    usar_broll: Optional[bool] = False


@router.post("/api/ai/batch-export")
async def batch_export(req: BatchExportRequest, background_tasks: BackgroundTasks):
    """
    Exporta todos os cortes de um lote em paralelo, limitado a 2 renders
    simultâneos pelo semáforo para não saturar FFmpeg/GPU.
    Erros por corte são salvos no DB (export_log) sem abortar o lote.
    """
    if not req.cortes:
        raise HTTPException(status_code=400, detail="Lista de cortes vazia")

    caminho_video = os.path.join(DIRETORIO_VIDEOS, f"{req.id_video}.mp4")
    if not os.path.exists(caminho_video):
        for ext in [".mov", ".avi", ".mkv", ".webm"]:
            alt = os.path.join(DIRETORIO_VIDEOS, f"{req.id_video}{ext}")
            if os.path.exists(alt):
                caminho_video = alt
                break
        else:
            raise HTTPException(status_code=404, detail="Vídeo fonte não encontrado")

    async def _exportar_um(corte: dict) -> dict:
        segments = corte.get("segments_to_keep", [])
        if not segments:
            return {"titulo": corte.get("titulo"), "status": "erro", "erro": "segments_to_keep ausente"}

        primeiro = segments[0]
        ultimo   = segments[-1]
        output_id     = f"{req.id_video}_viral_{int(float(primeiro['start']))}_{int(float(ultimo['end']))}"
        caminho_saida = os.path.join(DIRETORIO_CORTES, f"{output_id}.mp4")
        t0 = time.time()

        async with _batch_semaphore:
            try:
                loop = asyncio.get_running_loop()
                caminho_saida, duracao_final = await loop.run_in_executor(
                    _ffmpeg_executor,
                    ffmpeg_service.concatenar_segmentos,
                    caminho_video,
                    caminho_saida,
                    segments,
                    corte.get("focus_x", req.focus_x),
                    corte.get("headline"),
                )
                elapsed = round(time.time() - t0, 1)
                log.info("[Batch] %s exportado em %ss (%.1fs editado)", output_id, elapsed, duracao_final)

                # Salva VTT se synced_transcript presente
                synced = corte.get("synced_transcript")
                vtt_url = None
                if synced:
                    vtt_content = _gerar_vtt_sincronizado(synced)
                    vtt_path = os.path.join(DIRETORIO_CORTES, f"{output_id}.vtt")
                    with open(vtt_path, "w", encoding="utf-8") as f:
                        f.write(vtt_content)
                    vtt_url = f"/uploads/cortes/{output_id}.vtt"

                # Persiste no banco
                try:
                    with get_db_session() as db:
                        clip = ClipGerado(
                            id=output_id,
                            video_id=req.id_video,
                            cut_id=corte.get("cut_id"),
                            titulo=corte.get("titulo"),
                            viral_score=corte.get("viral_score"),
                            keyword_broll=corte.get("keyword_broll"),
                            raw_start=str(float(primeiro["start"])),
                            raw_end=str(float(ultimo["end"])),
                            duracao_editada=round(duracao_final, 2),
                            caminho_clip=caminho_saida,
                            caminho_vtt=os.path.join(DIRETORIO_CORTES, f"{output_id}.vtt") if vtt_url else None,
                            segments_to_keep=segments,
                            synced_transcript=synced,
                            status="pronto",
                        )
                        db.add(clip)
                except Exception as db_err:
                    log.warning("[Batch] DB write falhou para %s: %s", output_id, db_err)

                return {
                    "output_id": output_id,
                    "titulo": corte.get("titulo"),
                    "status": "pronto",
                    "duracao_editada": round(duracao_final, 2),
                    "video_url": f"/uploads/cortes/{output_id}.mp4",
                    "vtt_url": vtt_url,
                    "elapsed_s": elapsed,
                }

            except Exception as e:
                err_msg = str(e)
                log.error("[Batch] Falha exportando %s: %s", output_id, err_msg)
                # Salva log de erro no banco para o usuário consultar
                try:
                    with get_db_session() as db:
                        clip = db.query(ClipGerado).filter(ClipGerado.id == output_id).first()
                        if clip:
                            clip.status = "erro"
                            clip.export_log = {"erro": err_msg, "ts": datetime.now(timezone.utc).isoformat()}
                        else:
                            db.add(ClipGerado(
                                id=output_id,
                                video_id=req.id_video,
                                titulo=corte.get("titulo"),
                                status="erro",
                                export_log={"erro": err_msg, "ts": datetime.now(timezone.utc).isoformat()},
                            ))
                except Exception:
                    pass
                return {"output_id": output_id, "titulo": corte.get("titulo"), "status": "erro", "erro": err_msg}

    resultados = await asyncio.gather(*[_exportar_um(c) for c in req.cortes])
    prontos = [r for r in resultados if r["status"] == "pronto"]
    erros   = [r for r in resultados if r["status"] == "erro"]

    return {
        "sucesso": True,
        "total": len(req.cortes),
        "prontos": len(prontos),
        "erros": len(erros),
        "resultados": resultados,
    }