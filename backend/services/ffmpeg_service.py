import subprocess
import json
import os

DIRETORIO_AUDIOS = "uploads/audios"

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

def extrair_audio_para_ia(caminho_video, nome_arquivo_base):
    try:
        nome_audio = f"{nome_arquivo_base}.mp3"
        caminho_audio = os.path.join(DIRETORIO_AUDIOS, nome_audio)
        
        comando = [
            "ffmpeg", "-i", caminho_video,     
            "-vn", "-acodec", "libmp3lame", 
            "-q:a", "2", "-y", caminho_audio            
        ]
        
        subprocess.run(comando, capture_output=True, check=True)
        return nome_audio
    except Exception as erro:
        print(f"Erro ao extrair áudio: {erro}")
        return None