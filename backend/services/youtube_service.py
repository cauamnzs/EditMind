import yt_dlp

def baixar_video(url: str, caminho_final: str):
    opcoes_download = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': caminho_final,
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(opcoes_download) as ydl:
        ydl.extract_info(url, download=True)
        