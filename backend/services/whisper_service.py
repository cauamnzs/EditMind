import whisper
import os

def transcrever_audio(caminho_mp3: str) -> str:
    """
    Recebe o caminho de um arquivo de áudio e devolve o texto transcrito.
    """
    print(f"[WHISPER] Iniciando transcrição do arquivo: {caminho_mp3}")
    
    if not os.path.exists(caminho_mp3):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_mp3}")

    try:
        # Carrega o modelo 'base' (rápido e leve, ideal para a apresentação rodar liso no seu PC)
        # Na primeira execução, ele vai baixar ~500MB de modelo automaticamente.
        modelo = whisper.load_model("base")
        
        # Faz a mágica acontecer
        resultado = modelo.transcribe(caminho_mp3, language="pt") # Forçamos português para ser mais rápido
        
        texto_final = resultado["text"].strip()
        print("[WHISPER] Transcrição concluída com sucesso!")
        
        return texto_final

    except Exception as e:
        print(f"[WHISPER] Erro na transcrição: {e}")
        return f"Erro ao transcrever: {e}"