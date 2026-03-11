import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
CHAVE_API = os.getenv("OPENROUTER_API_KEY")

def sugerir_cortes(texto_transcricao: str) -> dict:
    print("[LLM] Analisando o texto via OpenRouter (Gemini Gratuito)...")

    if not CHAVE_API:
        print("[LLM] Erro: Chave OPENROUTER_API_KEY não encontrada no .env")
        return {"inicio": "00:03", "fim": "00:15", "motivo": "Modo Simulação (Falta de Key)"}

    try:
        # Chamada direta via API para não precisar instalar mais nenhuma biblioteca pesada
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {CHAVE_API}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000", # Necessário para alguns modelos no OpenRouter
                "X-Title": "EditMind"
            },
            data=json.dumps({
                "model": "google/gemini-2.0-flash-lite-preview-05-02:free",
                "messages": [
                    {
                        "role": "system", 
                        "content": "Você é um editor de vídeos virais. Responda APENAS em JSON."
                    },
                    {
                        "role": "user", 
                        "content": f"Com base nesta transcrição: '{texto_transcricao}', sugira um corte viral de 15 segundos. Responda apenas o JSON com as chaves: 'inicio' (MM:SS), 'fim' (MM:SS) e 'motivo'."
                    }
                ]
            })
        )
        
        resultado = response.json()
        
        # Pega o texto da resposta
        texto_ai = resultado['choices'][0]['message']['content']
        
        # Limpa o texto (remove ```json ou espaços extras)
        texto_limpo = texto_ai.replace("```json", "").replace("```", "").strip()
        
        # Converte para dicionário Python
        corte_json = json.loads(texto_limpo)
        
        print("[LLM] Corte real sugerido com sucesso!")
        return corte_json

    except Exception as e:
        print(f"[LLM] Erro na chamada do OpenRouter: {e}")
        return {
            "inicio": "00:00", 
            "fim": "00:15", 
            "motivo": "Os primeiros 15s são o gancho principal (Backup de Segurança)."
        }