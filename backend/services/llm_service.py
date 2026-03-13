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
    """
    Analisa a transcrição e gera o melhor gancho.
    Agora com extrator blindado contra textos chatos da IA.
    """
    print("🧠 [Brain Engine] Enviando transcrição para o OpenRouter (Gemini Flash)...")

    # Proteção: Se o vídeo for mudo
    if not transcricao or len(transcricao.strip()) < 50:
        return {
            "inicio": "00:00", "fim": "00:00", 
            "gancho": "Áudio Insuficiente",
            "motivo": "O vídeo não possui falas suficientes para análise."
        }
    
    prompt_sistema = """
    Você é o Diretor de Estratégia do EditMind. 
    Transforme vídeos longos em cortes virais.
    
    REGRA DE OURO: Retorne APENAS um objeto JSON válido. Use EXATAMENTE estas chaves, sem markdown:
    {
        "inicio": "MM:SS",
        "fim": "MM:SS",
        "gancho": "A frase de impacto para os primeiros 3 segundos",
        "motivo": "Explicação técnica da retenção"
    }
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                # Aqui está o link do Ngrok puxado do .env com sucesso!
                "HTTP-Referer": NGROK_URL, 
                "X-Title": "EditMind Local"
            },
            data=json.dumps({
                "model": MODELO_IA,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": f"Transcrição:\n{transcricao}"}
                ]
            })
        )

        if response.status_code == 200:
            resultado = response.json()
            conteudo_texto = resultado['choices'][0]['message']['content']
            
            # EXTRATOR BLINDADO: Pega só o que está entre { e }
            match = re.search(r'\{.*\}', conteudo_texto, re.DOTALL)
            
            if match:
                texto_limpo = match.group(0)
                corte_final = json.loads(texto_limpo)
                print(f"✅ [Brain Engine] Sucesso! Corte: {corte_final.get('inicio', '00:00')} - {corte_final.get('fim', '00:00')}")
                return corte_final
            else:
                print("❌ [Erro LLM]: A IA não enviou um JSON. Resposta bruta:")
                print(conteudo_texto)
                return {
                    "inicio": "00:00", "fim": "00:00", 
                    "gancho": "Erro de Formato",
                    "motivo": "A IA não respeitou a estrutura JSON."
                }
        else:
            print(f"❌ [Erro OpenRouter]: {response.status_code} - {response.text}")
            return {
                "inicio": "00:00", "fim": "00:00", 
                "gancho": "Erro na API",
                "motivo": f"Código: {response.status_code}"
            }

    except Exception as e:
        print(f"❌ [Erro Crítico LLM]: {str(e)}")
        return {
            "inicio": "00:00", "fim": "00:00", 
            "gancho": "Falha de Conexão",
            "motivo": str(e)
        }