from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import uuid
import subprocess
import json
import yt_dlp

# IMPORTANDO OS CÉREBROS DA IA (Nossas novas pastas)
from services import whisper_service
from services import llm_service

app = FastAPI(title="EditMind API")

# PILAR 1: Permissão de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração de Pastas
DIRETORIO_VIDEOS = "uploads/videos"
DIRETORIO_AUDIOS = "uploads/audios"
os.makedirs(DIRETORIO_VIDEOS, exist_ok=True)
os.makedirs(DIRETORIO_AUDIOS, exist_ok=True)

# --- FUNÇÃO 1: Extração de Metadados ---
def extrair_metadados_video(caminho_arquivo):
    try:
        comando = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", caminho_arquivo
        ]
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
        dados = json.loads(resultado.stdout)

        duracao = float(dados['format']['duration'])
        resolucao = "Desconhecida"
        fps_final = "Desconhecido"
        
        for stream in dados.get('streams', []):
            if stream.get('codec_type') == 'video':
                largura = stream.get('width')
                altura = stream.get('height')
                resolucao = f"{largura}x{altura}"
                
                fps_bruto = stream.get('r_frame_rate', '0/1')
                partes = fps_bruto.split('/')
                if len(partes) == 2 and int(partes[1]) != 0:
                    fps_final = round(int(partes[0]) / int(partes[1]), 2)
                break
                
        return {"duracao_segundos": round(duracao, 2), "resolucao": resolucao, "fps": fps_final}
    except Exception as e:
        return {"erro": str(e)}

# --- FUNÇÃO 2: A Mágica do Áudio ---
def extrair_audio_para_ia(caminho_video, nome_arquivo_base):
    try:
        nome_audio = f"{nome_arquivo_base}.mp3"
        caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
        
        comando = [
            "ffmpeg",
            "-i", caminho_video,     
            "-vn",                   
            "-acodec", "libmp3lame", 
            "-q:a", "2",             
            "-y",                    
            caminho_audio            
        ]
        
        subprocess.run(comando, capture_output=True, check=True)
        return nome_audio
    except Exception as erro:
        print(f"Erro ao extrair áudio: {erro}")
        return None

# ==========================================
# ROTAS DA API
# ==========================================

# ROTA 1: Upload Manual
@app.post("/api/upload")
async def receber_video_upload(arquivo: UploadFile = File(...)):
    if not arquivo.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Formato inválido. O sistema aceita apenas vídeos.")

    extensao_arquivo = arquivo.filename.split(".")[-1]
    id_unico = str(uuid.uuid4())
    nome_seguro_video = f"{id_unico}.{extensao_arquivo}"
    caminho_final_video = os.path.join(DIRETORIO_VIDEOS, nome_seguro_video)

    try:
        with open(caminho_final_video, "wb") as espaco_memoria:
            shutil.copyfileobj(arquivo.file, espaco_memoria)
    except Exception as erro_sistema:
        raise HTTPException(status_code=500, detail=f"Erro interno ao salvar: {str(erro_sistema)}")
    finally:
        arquivo.file.close()

    tamanho_em_megabytes = round(os.path.getsize(caminho_final_video) / (1024 * 1024), 2)
    metadados = extrair_metadados_video(caminho_final_video)
    nome_audio_gerado = extrair_audio_para_ia(caminho_final_video, id_unico)

    # ---------------------------------------------------------
    # 🔥 O MOTOR DA INTELIGÊNCIA ARTIFICIAL ENTRA AQUI 🔥
    # ---------------------------------------------------------
    caminho_do_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio_gerado)
    
    # 1. Ouvir
    texto_transcrito = whisper_service.transcrever_audio(caminho_do_audio)
    # 2. Pensar
    corte_sugerido = llm_service.sugerir_cortes(texto_transcrito)
    # ---------------------------------------------------------

    # Devolvemos o Contrato JSON atualizado com as chaves da IA
    return {
        "sucesso": True, # Mudamos de 'status' para 'sucesso' para bater com o contrato
        "mensagem": "Vídeo processado e IA aplicada com sucesso!",
        "video_salvo": nome_seguro_video,
        "tamanho_mb": tamanho_em_megabytes,
        "detalhes_tecnicos": metadados,
        # As chaves que o Front-end vai usar na Sexta-feira:
        "transcricao": texto_transcrito,
        "corte_sugerido": corte_sugerido
    }

# --- NOVA ROTA: YOUTUBE DOWNLOADER ---
class DadosYoutube(BaseModel):
    url: str

@app.post("/api/download-youtube")
async def baixar_video_youtube(dados: DadosYoutube):
    if not "youtube.com" in dados.url and not "youtu.be" in dados.url:
         raise HTTPException(status_code=400, detail="Por favor, insira um link válido do YouTube.")
         
    id_unico = str(uuid.uuid4())
    nome_seguro_video = f"yt_{id_unico}.mp4"
    caminho_final_video = os.path.join(DIRETORIO_VIDEOS, nome_seguro_video)
    
    opcoes_download = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': caminho_final_video,
        'merge_output_format': 'mp4',
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(opcoes_download) as ydl:
            ydl.extract_info(dados.url, download=True)
            
        tamanho_em_megabytes = round(os.path.getsize(caminho_final_video) / (1024 * 1024), 2)
        metadados = extrair_metadados_video(caminho_final_video)
        nome_audio_gerado = extrair_audio_para_ia(caminho_final_video, f"yt_{id_unico}")

        # 🔥 A IA TAMBÉM RODA NOS VÍDEOS DO YOUTUBE 🔥
        caminho_do_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio_gerado)
        texto_transcrito = whisper_service.transcrever_audio(caminho_do_audio)
        corte_sugerido = llm_service.sugerir_cortes(texto_transcrito)

        return {
            "sucesso": True,
            "mensagem": "Download do YouTube processado com IA!",
            "video_salvo": nome_seguro_video,
            "tamanho_mb": tamanho_em_megabytes,
            "detalhes_tecnicos": metadados,
            "transcricao": texto_transcrito,
            "corte_sugerido": corte_sugerido
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao baixar do YouTube: {str(e)}")