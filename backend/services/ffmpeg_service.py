import subprocess
import json
import os
import re
import shutil
import time
import logging
from functools import lru_cache
from typing import Optional, List, Tuple

log = logging.getLogger("editmind.ffmpeg")

DIRETORIO_AUDIOS    = "uploads/audios"
DIRETORIO_CORTES    = "uploads/cortes"
DIRETORIO_TEMP_CLIPS = "uploads/temp_clips"
os.makedirs(DIRETORIO_CORTES, exist_ok=True)
os.makedirs(DIRETORIO_TEMP_CLIPS, exist_ok=True)

def _run_ffmpeg(cmd: list, label: str = "ffmpeg") -> subprocess.CompletedProcess:
    """Executa FFmpeg com log estruturado de tempo e encoder usado."""
    t0 = time.time()
    encoder = next((cmd[i+1] for i, c in enumerate(cmd) if c == "-c:v" and i+1 < len(cmd)), "unknown")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        elapsed = round(time.time() - t0, 2)
        gpu = "GPU(nvenc)" if "nvenc" in encoder else "CPU(libx264)"
        log.info("[%s] %s — %.2fs — encoder=%s", label, gpu, elapsed, encoder)
        return result
    except subprocess.CalledProcessError as e:
        elapsed = round(time.time() - t0, 2)
        log.error("[%s] FALHOU após %.2fs — stderr: %s", label, elapsed, (e.stderr or "")[-300:])
        raise

def _get_duracao_real(caminho: str) -> float:
    """Mede a duração exata do arquivo gerado via ffprobe."""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", caminho]
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0

def _encoder_params(use_nvenc: bool) -> list:
    """Retorna parâmetros de encoder: h264_nvenc (GPU) ou libx264 (CPU fallback)."""
    if use_nvenc:
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "23"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]

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
        
        _run_ffmpeg(comando, label="extrair_audio")
        return nome_audio
    except Exception as erro:
        log.error("[extrair_audio] %s", erro)
        return None

# ==========================================
# FUNÇÕES FASE 1 - CORTE VERTICAL
# ==========================================

@lru_cache(maxsize=64)
def _get_video_dims(caminho_video: str) -> Tuple[int, int]:
    """Retorna (largura, altura) reais do vídeo via ffprobe. Cacheado por caminho."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", caminho_video
        ]
        resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dados = json.loads(resultado.stdout)
        for stream in dados.get("streams", []):
            if stream.get("codec_type") == "video":
                return int(stream["width"]), int(stream["height"])
    except Exception as e:
        print(f"⚠️ [ffprobe] Falha detectando dims: {e}")
    return 1920, 1080  # fallback FullHD

def _calcular_crop(largura_orig: int, altura_orig: int, focus_x: int, resolucao_saida: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """
    Calcula crop 9:16 adaptado às dimensões reais do vídeo.
    Retorna (largura_crop, altura_crop, x_crop, y_crop).
    """
    largura_saida, altura_saida = resolucao_saida
    # Razão 9:16 na altura do vídeo original
    largura_crop = int(altura_orig * largura_saida / altura_saida)
    largura_crop = min(largura_crop, largura_orig)  # nunca maior que o vídeo
    largura_crop = max(largura_crop, 2)              # mínimo 2px (par)
    # Garante que largura_crop é par (necessário para libx264)
    if largura_crop % 2 != 0:
        largura_crop -= 1
    altura_crop = altura_orig
    x_max = largura_orig - largura_crop
    x_crop = int((focus_x / 100) * x_max)
    x_crop = max(0, min(x_crop, x_max))
    return largura_crop, altura_crop, x_crop, 0

def gerar_corte_vertical(
    caminho_video: str, 
    caminho_saida: str, 
    inicio_seg: float, 
    duracao: float,
    headline: Optional[str] = None,
    focus_x: int = 50,
    resolucao_saida: Tuple[int, int] = (1080, 1920)  # 9:16
) -> str:
    """
    Gera um corte vertical 9:16 com:
    - Crop inteligente baseado em focus_x (0-100)
    - Headline com drawtext (opcional)
    - Seek preciso para início do corte
    
    Returns:
        Caminho do arquivo gerado
    """
    print(f" [FFmpeg] Gerando corte vertical: {inicio_seg}s - {inicio_seg + duracao}s")
    print(f"   Focus X: {focus_x}% | Headline: {headline}")
    
    # Detecta dimensões reais do vídeo (suporta qualquer resolução)
    largura_saida, altura_saida = resolucao_saida
    largura_original, altura_original = _get_video_dims(caminho_video)
    largura_crop, altura_crop, x_crop, y_crop = _calcular_crop(
        largura_original, altura_original, focus_x, resolucao_saida
    )
    print(f"   Dims originais: {largura_original}x{altura_original} | Crop: {largura_crop}x{altura_crop}+{x_crop}")

    # Monta o filtro de vídeo
    filtros = []

    # 1. Crop para extrair área 9:16
    filtros.append(f"crop={largura_crop}:{altura_crop}:{x_crop}:{y_crop}")
    
    # 2. Scale para resolução final
    filtros.append(f"scale={largura_saida}:{altura_saida}:force_original_aspect_ratio=decrease,setsar=1:1")
    
    # 3. Headline com drawtext (se fornecido)
    if headline and headline.strip():
        texto_limpo = headline.replace("'", "\\'").replace(":", "\\:")
        drawtext = (
            f"drawtext=text='{texto_limpo}':"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize=72:"
            f"fontcolor=white:"
            f"borderw=8:bordercolor=black:"
            f"x=(w-text_w)/2:"
            f"y=100:"
            f"line_spacing=10"
        )
        filtros.append(drawtext)

    vf_string = ",".join(filtros)
    print(f"   Filtros: {vf_string[:100]}...")

    # Comando montado dinamicamente (sem índice fixo)
    comando = [
        "ffmpeg",
        "-ss", str(inicio_seg),
        "-t", str(duracao),
        "-i", caminho_video,
        "-vf", vf_string,
        *_encoder_params(use_nvenc=True),
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        caminho_saida
    ]
    
    try:
        _run_ffmpeg(comando, label="corte_vertical")
        log.info("[corte_vertical] Gerado: %s", caminho_saida)
        return caminho_saida
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg falhou: {e.stderr[-300:]}")


# ==========================================
# FUNÇÕES FASE 2 - JUMP CUT & B-ROLL
# ==========================================

def gerar_jump_cut(
    caminho_video: str,
    caminho_saida: str,
    inicio_seg: float,
    fim_seg: float,
    silencios: List[Tuple[float, float]],
    focus_x: int = 50
) -> str:
    """
    Gera corte removendo segmentos de silêncio (Jump Cut).
    
    Args:
        silencios: Lista de (inicio_silencio, fim_silencio) em segundos
        relativos ao início do vídeo original
    """
    print(f" [Jump Cut] Removendo {len(silencios)} silêncios")
    
    # Converte silêncios globais para relativos ao corte
    silencios_relativos = []
    for s_inicio, s_fim in silencios:
        if inicio_seg <= s_inicio < fim_seg:
            rel_inicio = s_inicio - inicio_seg
            rel_fim = min(s_fim, fim_seg) - inicio_seg
            if rel_fim > rel_inicio:
                silencios_relativos.append((rel_inicio, rel_fim))
    
    if not silencios_relativos:
        # Sem silêncios, apenas gera corte normal
        return gerar_corte_vertical(
            caminho_video, caminho_saida, 
            inicio_seg, fim_seg - inicio_seg,
            focus_x=focus_x
        )
    
    # Cria arquivo de concatenação
    duracao_total = fim_seg - inicio_seg
    segmentos_manter = []
    
    cursor = 0.0
    for s_inicio, s_fim in sorted(silencios_relativos):
        if s_inicio > cursor:
            segmentos_manter.append((cursor, s_inicio))
        cursor = s_fim
    
    if cursor < duracao_total:
        segmentos_manter.append((cursor, duracao_total))
    
    print(f"   Mantendo {len(segmentos_manter)} segmentos de fala")
    
    # Gera segmentos individuais
    arquivos_temp = []
    for i, (seg_inicio, seg_fim) in enumerate(segmentos_manter):
        temp_file = f"{caminho_saida}.seg{i}.mp4"
        dur_seg = seg_fim - seg_inicio
        
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(inicio_seg + seg_inicio),
            "-t", str(dur_seg),
            "-i", caminho_video,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            temp_file
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        arquivos_temp.append(temp_file)
    
    # Arquivo de concatenação
    concat_list = caminho_saida + ".concat.txt"
    with open(concat_list, 'w') as f:
        for arq in arquivos_temp:
            f.write(f"file '{arq}'\n")
    
    # Concatena
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        caminho_saida
    ]
    
    subprocess.run(cmd_concat, capture_output=True, check=True)
    
    # Limpa temp files
    for arq in arquivos_temp:
        if os.path.exists(arq):
            os.remove(arq)
    if os.path.exists(concat_list):
        os.remove(concat_list)
    
    return caminho_saida


def concatenar_segmentos(
    caminho_video: str,
    caminho_saida: str,
    segments_to_keep: List[dict],
    focus_x: int = 50,
    headline: Optional[str] = None,
    resolucao_saida: Tuple[int, int] = (1080, 1920)
) -> Tuple[str, float]:
    """
    Executa a renderização do JSON Editor Chefe:
    1. Recorta cada segmento de segments_to_keep individualmente
    2. Aplica crop 9:16 + scale com focus_x em cada segmento
    3. Concatena tudo numa única timeline limpa
    4. Adiciona headline opcional no topo

    Args:
        segments_to_keep: lista de {"start": float, "end": float} em segundos absolutos do vídeo original
    Returns:
        caminho do arquivo gerado e duração real
    """
    print(f"✂️ [Jump Cut Engine] {len(segments_to_keep)} segmentos para concatenar")

    if not segments_to_keep:
        raise ValueError("segments_to_keep vazio — nada para renderizar")

    largura_saida, altura_saida = resolucao_saida
    largura_original, altura_original = _get_video_dims(caminho_video)
    largura_crop, altura_crop, x_crop, y_crop = _calcular_crop(
        largura_original, altura_original, focus_x, resolucao_saida
    )
    print(f"   [Concat] Dims: {largura_original}x{altura_original} | Crop: {largura_crop}x{altura_crop}+{x_crop}")

    filtros_base = [
        f"crop={largura_crop}:{altura_crop}:{x_crop}:{y_crop}",
        f"scale={largura_saida}:{altura_saida}:force_original_aspect_ratio=decrease,setsar=1:1"
    ]

    if headline and headline.strip():
        texto_limpo = headline.replace("'", "\\'").replace(":", "\\:")
        filtros_base.append(
            f"drawtext=text='{texto_limpo}':"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontsize=72:fontcolor=white:borderw=8:bordercolor=black:"
            f"x=(w-text_w)/2:y=100"
        )

    vf_string = ",".join(filtros_base)

    # Gera um arquivo temporário por segmento (re-encode limpo)
    arquivos_temp = []
    base_temp = caminho_saida + ".seg"

    for i, seg in enumerate(segments_to_keep):
        s_start = float(seg["start"])
        s_end   = float(seg["end"])
        s_dur   = s_end - s_start
        if s_dur <= 0.05:
            print(f"   ⚠️  Segmento {i} muito curto ({s_dur:.3f}s) — pulado")
            continue

        temp_path = f"{base_temp}{i}.mp4"
        enc = _encoder_params(use_nvenc=True)
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{s_start:.3f}",
            "-t",  f"{s_dur:.3f}",
            "-i",  caminho_video,
            "-vf", vf_string,
            *enc,
            "-c:a", "aac", "-b:a", "128k",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            temp_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                # Fallback para libx264 se nvenc não disponível
                enc_cpu = _encoder_params(use_nvenc=False)
                cmd_cpu = [
                    "ffmpeg", "-y",
                    "-ss", f"{s_start:.3f}",
                    "-t",  f"{s_dur:.3f}",
                    "-i",  caminho_video,
                    "-vf", vf_string,
                    *enc_cpu,
                    "-c:a", "aac", "-b:a", "128k",
                    "-avoid_negative_ts", "make_zero",
                    "-movflags", "+faststart",
                    temp_path
                ]
                subprocess.run(cmd_cpu, capture_output=True, text=True, check=True)
            arquivos_temp.append(temp_path)
            print(f"   ✅ Segmento {i}: {s_start:.2f}s → {s_end:.2f}s ({s_dur:.2f}s)")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Segmento {i} falhou: {e.stderr[-200:]}")

    if not arquivos_temp:
        raise Exception("Nenhum segmento gerado — todos falharam ou foram pulados")

    if len(arquivos_temp) == 1:
        shutil.move(arquivos_temp[0], caminho_saida)
        print(f"✅ [Concat] 1 segmento → {caminho_saida}")
        duracao_real = _get_duracao_real(caminho_saida)
        print(f"   ⏱  Duração real medida: {duracao_real:.3f}s")
        return caminho_saida, duracao_real

    # Gera arquivo de lista para concat demuxer
    concat_list = caminho_saida + ".concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for arq in arquivos_temp:
            f.write(f"file '{os.path.abspath(arq)}'\n")

    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        "-movflags", "+faststart",
        caminho_saida
    ]

    try:
        subprocess.run(cmd_concat, capture_output=True, text=True, check=True)
        print(f"✅ [Concat] {len(arquivos_temp)} segmentos → {caminho_saida}")
    except subprocess.CalledProcessError as e:
        print(f"❌ [Concat Error]: {e.stderr[-300:]}")
        raise Exception(f"Concatenação FFmpeg falhou: {e.stderr[-300:]}")
    finally:
        # Limpeza de temp files e lista
        for arq in arquivos_temp:
            if os.path.exists(arq):
                os.remove(arq)
        if os.path.exists(concat_list):
            os.remove(concat_list)

    duracao_real = _get_duracao_real(caminho_saida)
    print(f"   ⏱  Duração real medida: {duracao_real:.3f}s")
    return caminho_saida, duracao_real


def adicionar_broll(
    caminho_video: str,
    caminho_saida: str,
    overlays: List[dict]  # [{"imagem": path, "inicio": sec, "duracao": sec}]
) -> str:
    """
    Adiciona imagens B-Roll como overlay no vídeo.
    
    Args:
        overlays: Lista de dict com imagem, inicio e duracao
    """
    print(f" [B-Roll] Adicionando {len(overlays)} overlays")
    
    if not overlays:
        shutil.copy2(caminho_video, caminho_saida)
        return caminho_saida
    
    # Constroi filtro complexo
    inputs = ["-i", caminho_video]
    for ov in overlays:
        inputs.extend(["-i", ov["imagem"]])
    
    # Filtro overlay
    filtros = ["[0:v]format=yuva420p[base]"]
    stream_atual = "base"
    
    for i, ov in enumerate(overlays):
        idx = i + 1
        inicio = ov["inicio"]
        duracao = ov["duracao"]
        
        # Overlay com fade in/out
        overlay_filter = (
            f"[{stream_atual}][{idx}:v]overlay="
            f"(W-w)/2:(H-h)/2:"
            f"enable='between(t,{inicio},{inicio+duracao})':"
            f"format=auto[ov{i}]"
        )
        filtros.append(overlay_filter)
        stream_atual = f"ov{i}"
    
    filtros.append(f"[{stream_atual}]format=yuv420p[final]")
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filtros),
        "-map", "[final]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "copy",
        caminho_saida
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    return caminho_saida


def adicionar_headline(
    caminho_video: str,
    caminho_saida: str,
    headline: str
) -> str:
    """
    Adiciona headline com drawtext no topo do vídeo.
    Usado quando o corte já foi gerado mas precisa adicionar título.
    """
    print(f" [Headline] Adicionando: {headline}")
    
    if not headline or not headline.strip():
        shutil.copy2(caminho_video, caminho_saida)
        return caminho_saida
    
    # Escapa caracteres especiais
    texto_limpo = headline.replace("'", "\\'").replace(":", "\\:")
    
    # Usa fonte do sistema ou fonte padrão
    fonte = "DejaVuSans-Bold"
    
    # Filtro drawtext com estilo viral
    drawtext = (
        f"drawtext=text='{texto_limpo}':"
        f"font={fonte}:"
        f"fontsize=72:"
        f"fontcolor=white:"
        f"borderw=8:bordercolor=black:"
        f"x=(w-text_w)/2:"
        f"y=100:"
        f"line_spacing=10"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", caminho_video,
        "-vf", drawtext,
        *_encoder_params(use_nvenc=True),
        "-c:a", "copy",
        caminho_saida
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        print(f" [Headline] Adicionada com sucesso")
        return caminho_saida
    except subprocess.CalledProcessError as e:
        print(f" [Headline Error]: {e.stderr}")
        shutil.copy2(caminho_video, caminho_saida)
        return caminho_saida