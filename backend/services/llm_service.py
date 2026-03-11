import os
import json
from dotenv import load_dotenv
from google import genai

# Carrega as variáveis de ambiente
load_dotenv()
CHAVE_API = os.getenv("GEMINI_API_KEY")

# Inicializa o cliente com a NOVA biblioteca
if CHAVE_API:
    client = genai.Client(api_key=CHAVE_API)
else:
    client = None

def sugerir_cortes(texto_transcricao: str) -> dict:
    """
    Envia a transcrição para a IA (Nova API) e pede para ela achar o melhor corte.
    Devolve um dicionário (JSON) padronizado.
    """
    print("[LLM] Analisando o texto com a nova API do Gemini...")

    if not client:
        print("[LLM] AVISO: Chave da API não encontrada. Retornando corte fake de teste.")
        return {"inicio": "00:05", "fim": "00:15", "motivo": "Simulação por falta de API Key"}

    prompt = f"""
    Você é um editor de vídeos virais estilo OpusClip.
    Leia a transcrição abaixo e identifique o trecho de 10 a 20 segundos mais impactante, 
    que prenda a atenção (um gancho forte).

    Transcrição:
    "{texto_transcricao}"

    Regra OBRIGATÓRIA: Responda APENAS com um formato JSON válido, sem markdown, contendo as exatas chaves:
    "inicio" (formato MM:SS), "fim" (formato MM:SS), "motivo" (uma frase curta explicando).
    """

    try:
        # Usando o modelo atualizado da nova SDK
        resposta = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        
        # Limpa a resposta da IA caso ela mande formatação
        texto_limpo = resposta.text.replace("```json", "").replace("```", "").strip()
        corte_json = json.loads(texto_limpo)
        
        print("[LLM] Corte sugerido com sucesso!")
        return corte_json

    except Exception as e:
        print(f"[LLM] Erro ao analisar corte: {e}")
        return {"inicio": "00:00", "fim": "00:15", "motivo": "Os primeiros 15s são o gancho principal."}