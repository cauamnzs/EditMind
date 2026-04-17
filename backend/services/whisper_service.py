from faster_whisper import WhisperModel
import os
import gc
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from functools import lru_cache

# ==========================================
# CONFIGURAÇÃO DE PERFORMANCE RTX 4060
# ==========================================
@dataclass
class WhisperConfig:
    """Configurações otimizadas para RTX 4060 (8GB VRAM)"""
    model_size: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "float16"
    beam_size: int = 5
    best_of: int = 5
    patience: float = 1.0
    condition_on_previous_text: bool = True
    initial_prompt: Optional[str] = None

# ==========================================
# GERENCIAMENTO LAZY DO MODELO
# ==========================================
class WhisperEngine:
    """
    Singleton para gerenciar o modelo Whisper na VRAM.
    Implementa lazy loading e cache de transcrições.
    """
    _instance = None
    _model = None
    _config = None
    _last_used = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config = WhisperConfig()
        return cls._instance
    
    def _load_model(self):
        """Carrega o modelo na VRAM apenas quando necessário."""
        if self._model is None:
            print("⚡ [Whisper Engine] Aquecendo CUDA Cores... Carregando 'large-v3'")
            try:
                # Libera memória antes de carregar
                gc.collect()
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                
                self._model = WhisperModel(
                    self._config.model_size,
                    device=self._config.device,
                    compute_type=self._config.compute_type,
                    cpu_threads=4 if self._config.device == "cpu" else 0,
                    num_workers=2
                )
                print(f"✅ [Whisper Engine] {self._config.model_size} carregado na VRAM!")
                
                # Log VRAM usage
                if torch.cuda.is_available():
                    vram_used = torch.cuda.memory_allocated() / 1024**3
                    print(f"📊 [VRAM] Uso atual: {vram_used:.2f} GB")
                    
            except Exception as e:
                print(f"⚠️ [Whisper Engine] Falha CUDA: {e}. Fallback CPU...")
                self._config.device = "cpu"
                self._config.compute_type = "int8"
                self._model = WhisperModel(
                    "base",
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=4
                )
        return self._model
    
    def unload(self):
        """Descarrega modelo da VRAM para liberar memória."""
        if self._model is not None:
            del self._model
            self._model = None
            gc.collect()
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            print("🧹 [Whisper Engine] Modelo descarregado da VRAM")
    
    @property
    def model(self):
        return self._load_model()

# Instância global do engine
whisper_engine = WhisperEngine()

def transcrever_audio(caminho_audio: str) -> str:
    """
    Transcreve áudio usando VAD para ignorar silêncios.
    Otimizado para RTX 4060 com float16.
    """
    print(f"🚀 [Whisper] Transcrevendo: {os.path.basename(caminho_audio)}")
    
    try:
        cfg = whisper_engine._config
        segmentos, info = whisper_engine.model.transcribe(
            caminho_audio,
            beam_size=cfg.beam_size,
            best_of=cfg.best_of,
            patience=cfg.patience,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=300
            ),
            condition_on_previous_text=cfg.condition_on_previous_text,
            initial_prompt=cfg.initial_prompt,
            word_timestamps=False
        )
        
        print(f"🎙️ [Whisper] Idioma: '{info.language}' ({info.language_probability*100:.1f}%)")
        
        texto_completo = ""
        for segmento in segmentos:
            texto_completo += segmento.text.strip() + " "
        
        return texto_completo.strip()
        
    except Exception as e:
        print(f"❌ [Whisper Error]: {str(e)}")
        return "Erro ao transcrever áudio."

def transcrever_com_timestamps(caminho_audio: str) -> Tuple[str, List[Dict]]:
    """
    Retorna transcrição completa + lista de segmentos com timestamps.
    ESSENCIAL para Jump Cut Inteligente (Fase 2).
    
    Returns:
        (texto_completo, lista_de_segmentos)
        cada segmento: {start, end, text, words?}
    """
    print(f"⏱️ [Whisper TS] Analisando timestamps: {os.path.basename(caminho_audio)}")
    
    try:
        cfg = whisper_engine._config
        segmentos_raw, info = whisper_engine.model.transcribe(
            caminho_audio,
            beam_size=cfg.beam_size,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300),  # Mais sensível
            word_timestamps=True,  # ESSENCIAL para jump cut preciso
            condition_on_previous_text=True
        )
        
        print(f"🎙️ [Whisper TS] Idioma: '{info.language}' ({info.language_probability*100:.1f}%)")
        
        texto_completo = ""
        segmentos_list = []
        
        for seg in segmentos_raw:
            texto_completo += seg.text.strip() + " "
            segmento_dict = {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in (seg.words or [])
                ]
            }
            segmentos_list.append(segmento_dict)
        
        print(f"📊 [Whisper TS] Total segmentos: {len(segmentos_list)}")
        return texto_completo.strip(), segmentos_list
        
    except Exception as e:
        print(f"❌ [Whisper TS Error]: {str(e)}")
        return "Erro", []

def extrair_momentos_sem_fala(segmentos: List[Dict], min_silence_sec: float = 0.5) -> List[Tuple[float, float]]:
    """
    Analisa segmentos com timestamps e retorna gaps de silêncio.
    ESSENCIAL para Jump Cut Inteligente.
    
    Returns:
        Lista de tuplas (inicio_silencio, fim_silencio)
    """
    if not segmentos or len(segmentos) < 2:
        return []
    
    silencios = []
    
    for i in range(len(segmentos) - 1):
        fim_atual = segmentos[i]["end"]
        inicio_proximo = segmentos[i + 1]["start"]
        gap = inicio_proximo - fim_atual
        
        if gap >= min_silence_sec:
            silencios.append((fim_atual, inicio_proximo))
    
    print(f"🔇 [Silence Detect] Encontrados {len(silencios)} gaps > {min_silence_sec}s")
    return silencios