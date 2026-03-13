from faster_whisper import WhisperModel
import os

# ==========================================
# INICIALIZAÇÃO DO MOTOR NA VRAM
# ==========================================
# Com a RTX 4060, o float16 é o cenário ideal. 
# O large-v3 garante que o Llama/Gemini receba um texto perfeito para achar os ganchos.
print("⚡ [Whisper Engine] Aquecendo os CUDA Cores... Carregando 'large-v3'")
try:
    modelo = WhisperModel("large-v3", device="cuda", compute_type="float16")
    print("✅ [Whisper Engine] Modelo large-v3 carregado com sucesso na RTX!")
except Exception as e:
    print(f"⚠️ [Aviso Crítico] Falha ao injetar no CUDA. Caindo pra CPU. Erro: {e}")
    # Fallback caso dê algum BO de driver
    modelo = WhisperModel("base", device="cpu", compute_type="int8")

def transcrever_audio(caminho_audio):
    """
    Fatia o áudio usando VAD e processa tudo direto na GPU.
    """
    print(f"🚀 [Whisper] Extraindo DNA do áudio: {caminho_audio}...")
    
    try:
        # vad_filter=True ignora o silêncio, economizando processamento da placa
        segmentos, info = modelo.transcribe(
            caminho_audio, 
            beam_size=5, 
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        print(f"🎙️ [Whisper] Idioma mapeado: '{info.language}' ({info.language_probability * 100:.1f}% precisão)")
        
        texto_completo = ""
        
        # Faz o streaming no console pra você ver a placa de vídeo voando
        for segmento in segmentos:
            texto_limpo = segmento.text.strip()
            # print(f"[{segmento.start:.2f}s -> {segmento.end:.2f}s] {texto_limpo}") # Descomente se quiser ver linha por linha
            texto_completo += texto_limpo + " "
            
        return texto_completo.strip()

    except Exception as erro:
        print(f"❌ [ERRO F-WHISPER]: {str(erro)}")
        return "Erro ao transcrever o áudio."