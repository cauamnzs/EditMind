import requests
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
NGROK_URL = os.getenv("API_BASE_URL")

# --- CONFIGURAÇÃO ---
MODELO_IA = "openrouter/free"

def sugerir_cortes(transcricao):
    print("🧠 [Brain Engine] Buscando cortes virais padrão...")

    if not transcricao or len(transcricao.strip()) < 50:
        return []
    
    prompt_sistema = """
    Você é o Algoritmo Chefe do EditMind, especialista em retenção do TikTok e Reels.
    Analise a transcrição e extraia os 3 melhores cortes.
    
    REGRA DE OURO: Retorne APENAS um Array JSON válido com 3 objetos. Use EXATAMENTE estas chaves:
    [
      {
          "titulo": "Título Curto (Ex: O Segredo da Picanha)",
          "viral_score": 98, 
          "inicio": "00:10",
          "fim": "00:55",
          "gancho": "A frase exata que fisga nos primeiros 3 segundos",
          "motivo": "Explicação do gatilho psicológico (Pathos, Logos, etc)",
          "texto_corte": "A transcrição exata e completa de tudo o que foi dito neste trecho."
      }
    ]
    O viral_score deve ser um número de 70 a 99 baseando-se no potencial de viralização.
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": NGROK_URL, 
                "X-Title": "EditMind Local"
            },
            data=json.dumps({
                "model": MODELO_IA,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": f"Transcrição:\n{transcricao}"}
                ]
            }),
            timeout=60
        )

        if response.status_code == 200:
            resultado = response.json()
            conteudo_texto = resultado['choices'][0]['message']['content']
            match = re.search(r'\[.*\]', conteudo_texto, re.DOTALL)
            
            if match:
                return json.loads(match.group(0))
            return []
        return []
    except Exception as e:
        print(f"❌ Erro LLM: {str(e)}")
        return []