"""
EditMind — SSE Routes
Progresso em tempo real via Server-Sent Events.
Cada etapa do pipeline emite um evento sem precisar de WebSocket.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
import time
from typing import AsyncGenerator

router = APIRouter()

# Registry global: id_video -> asyncio.Queue de eventos
# A queue é criada pelo upload e consumida pelo cliente SSE.
_sse_queues: dict[str, asyncio.Queue] = {}


def criar_fila_sse(id_video: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _sse_queues[id_video] = q
    return q


def get_fila_sse(id_video: str) -> asyncio.Queue | None:
    return _sse_queues.get(id_video)


async def emitir_evento(id_video: str, etapa: str, mensagem: str, progresso: int = 0, dados: dict | None = None) -> None:
    """Emite evento SSE para o cliente que acompanha o id_video."""
    q = _sse_queues.get(id_video)
    if q is None:
        return
    evento = {
        "etapa": etapa,
        "mensagem": mensagem,
        "progresso": progresso,
        "ts": time.time(),
        **(dados or {}),
    }
    try:
        q.put_nowait(evento)
    except asyncio.QueueFull:
        pass  # cliente não está lendo — ignora sem bloquear pipeline


async def _gerar_stream(id_video: str) -> AsyncGenerator[str, None]:
    """Gera o stream SSE consumindo eventos da fila até receber 'done' ou timeout."""
    # Aguarda até 15s pela fila ser criada (frontend conecta antes do POST chegar)
    for _ in range(30):
        if id_video in _sse_queues:
            break
        yield ": waiting\n\n"
        await asyncio.sleep(0.5)
    else:
        yield f"data: {json.dumps({'etapa': 'erro', 'mensagem': 'Upload não iniciado — timeout'})}\n\n"
        return

    q = _sse_queues[id_video]
    timeout_total = 600  # 10 minutos máximo
    deadline = time.time() + timeout_total

    while time.time() < deadline:
        try:
            evento = await asyncio.wait_for(q.get(), timeout=30)
        except asyncio.TimeoutError:
            yield ": keep-alive\n\n"  # heartbeat para não fechar a conexão
            continue

        yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"

        if evento.get("etapa") in ("concluido", "erro"):
            _sse_queues.pop(id_video, None)
            break


@router.get("/api/upload/stream/{id_video}")
async def stream_progresso(id_video: str):
    """
    SSE endpoint — o frontend conecta aqui antes de enviar o arquivo.
    Recebe eventos: audio_extraido | transcricao | analise_ia | concluido | erro
    """
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # desativa buffer no Nginx
    }
    return StreamingResponse(
        _gerar_stream(id_video),
        media_type="text/event-stream",
        headers=headers,
    )
