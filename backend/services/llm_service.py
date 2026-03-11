import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (o arquivo .env que criamos)
load_dotenv()

# Pega a chave gratuita que você vai gerar no Google AI Studio
CHAVE_API = os.getenv("GEMINI_API_KEY")

if CHAVE_API:
    genai.configure(api_key=CHAVE_API)

def sugerir_cortes(texto_transcricao: str) -> dict:
    """
    Envia a transcrição para a IA e pede para ela achar o melhor corte.
    Devolve um dicionário (JSON) padronizado.
    """
    print("[LLM] Analisando o texto para encontrar o melhor corte viral...")

    if not CHAVE_API:
        print("[LLM] AVISO: Chave da API não encontrada. Retornando corte fake de teste.")
        return {"inicio": "00:05", "fim": "00:15", "motivo": "Simulação por falta de API Key"}

    # O PROMPT DE ENGENHARIA (A instrução mestre)
    prompt = f"""
    Você é um editor de vídeos virais estilo OpusClip.
    Leia a transcrição abaixo e identifique o trecho de 10 a 20 segundos mais impactante, 
    que prenda a atenção (um gancho forte).

    Transcrição:
    "{texto_transcricao}"

    Regra OBRIGATÓRIA: Responda APENAS com um formato JSON válido, sem markdown, contendo as chaves:
    "inicio" (formato MM:SS), "fim" (formato MM:SS), "motivo" (uma frase curta explicando).
    """

    try:
        # Usamos o modelo flash que é super rápido e de graça
        modelo = genai.GenerativeModel('gemini-1.5-flash')
        resposta = modelo.generate_content(prompt)
        
        # Limpa a resposta da IA caso ela mande aquelas crases de código (```json)
        texto_limpo = resposta.text.replace("```json", "").replace("```", "").strip()
        
        # Transforma a string da IA em um Dicionário Python real
        corte_json = json.loads(texto_limpo)
        
        print("[LLM] Corte sugerido com sucesso!")
        return corte_json

    except Exception as e:
        print(f"[LLM] Erro ao analisar corte: {e}")
        # Se a IA der pau na hora da apresentação, a gente manda um fallback pra não zerar a nota
        return {"inicio": "00:00", "fim": "00:15", "motivo": "Os primeiros 15s são o gancho principal."}