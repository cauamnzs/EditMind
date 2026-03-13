from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
import os
from services import ffmpeg_service

router = APIRouter()

DIRETORIO_VIDEOS = "uploads/videos"

class CorteSelecionado(BaseModel):
    id_video: str
    inicio: str
    fim: str
    gancho: str

@router.post("/api/video/fatiar")
async def processar_cortes_finais(cortes: List[CorteSelecionado], background_tasks: BackgroundTasks):
    if not cortes:
        raise HTTPException(status_code=400, detail="Nenhum corte selecionado.")

    try:
        for corte in cortes:
            caminho_original = os.path.join(DIRETORIO_VIDEOS, corte.id_video)
            
            if not os.path.exists(caminho_original):
                continue

            background_tasks.add_task(
                ffmpeg_service.cortar_video, 
                caminho_original, 
                corte.inicio, 
                corte.fim
            )

        return {"sucesso": True, "mensagem": f"Fatiando {len(cortes)} cortes! ⚡"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))