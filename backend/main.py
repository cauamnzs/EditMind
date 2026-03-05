from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
import subprocess
import json

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
os.makedirs(DIRETORIO_AUDIOS, exist_ok=True) # Nova pasta garantida no sistema

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
    """
    Usa o FFmpeg para ignorar o vídeo e salvar apenas a faixa de áudio em MP3.
    """
    try:
        nome_audio = f"{nome_arquivo_base}.mp3"
        caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
        
        # Comando do FFmpeg
        comando = [
            "ffmpeg",
            "-i", caminho_video,     # Entrada: o vídeo pesado
            "-vn",                   # Comando chave: Video No (ignora a imagem)
            "-acodec", "libmp3lame", # Força a conversão para MP3 leve
            "-q:a", "2",             # Qualidade do áudio (2 é excelente para voz)
            "-y",                    # Sobrescreve silenciosamente se já existir
            caminho_audio            # Saída: o arquivo final
        ]
        
        # Executa silenciosamente no terminal do Windows
        subprocess.run(comando, capture_output=True, check=True)
        return nome_audio
    except Exception as erro:
        print(f"Erro ao extrair áudio: {erro}")
        return None

# PILAR 2: Rota Principal de Upload
@app.post("/api/upload")
async def receber_video_upload(arquivo: UploadFile = File(...)):
    
    if not arquivo.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Formato inválido. O sistema aceita apenas vídeos.")

    # PILAR 3: Segurança e Salvamento
    extensao_arquivo = arquivo.filename.split(".")[-1]
    id_unico = str(uuid.uuid4()) # Separamos o ID para usar no vídeo e no áudio
    nome_seguro_video = f"{id_unico}.{extensao_arquivo}"
    caminho_final_video = os.path.join(DIRETORIO_VIDEOS, nome_seguro_video)

    try:
        with open(caminho_final_video, "wb") as espaco_memoria:
            shutil.copyfileobj(arquivo.file, espaco_memoria)
    except Exception as erro_sistema:
        raise HTTPException(status_code=500, detail=f"Erro interno ao salvar: {str(erro_sistema)}")
    finally:
        arquivo.file.close()

    # PILAR 4: Extrações em Segundo Plano
    tamanho_em_megabytes = round(os.path.getsize(caminho_final_video) / (1024 * 1024), 2)
    metadados = extrair_metadados_video(caminho_final_video)
    
    # É aqui que o áudio nasce!
    nome_audio_gerado = extrair_audio_para_ia(caminho_final_video, id_unico)

    return {
        "status": "sucesso",
        "mensagem": "Vídeo processado e áudio extraído com sucesso!",
        "nome_original": arquivo.filename,
        "video_salvo": nome_seguro_video,
        "audio_salvo": nome_audio_gerado,
        "tamanho_mb": tamanho_em_megabytes,
        "detalhes_tecnicos": metadados
    }