import requests
import json

# --- CONFIGURAÇÃO ---
OPENROUTER_API_KEY = "OPENROUTER_API_KEY=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" 
MODELO_IA = "google/gemini-flash-1.5-exp:free" 

def sugerir_cortes(transcricao):
    """
    Analisa a transcrição e gera ganchos baseados no DNA do conteúdo, 
    focando 100% em retenção para Shorts/TikTok.
    """
    
    prompt_sistema = """
    Você é o Diretor de Estratégia do EditMind. Sua função é transformar vídeos longos em 'bombas de retenção' curtas.
    
    ESQUEÇA NICHOS GENÉRICOS. Foque no seguinte:
    1. CONTEXTO DO CONTEÚDO: Identifique quem está falando e qual a 'dor' ou 'desejo' do público desse vídeo.
    2. HOOK ENGINEERING: O gancho (hook) deve ser moldado para o público específico (Ex: Se for Maromba, use ganchos de disciplina/resultado. Se for Churrasco, use ganchos de técnica/sabor).
    3. ESTRUTURA DE CORTE: O início deve ser uma quebra de padrão e o fim deve ser um 'cliffhanger' (gancho para o próximo).

    FORMATO DE RESPOSTA (JSON PURO):
    [
      {
        "gancho_viral": "A frase de impacto para os primeiros 3 segundos",
        "inicio": "MM:SS",
        "fim": "MM:SS",
        "por_que_viraliza": "Explicação técnica da psicologia de retenção usada",
        "estilo_edicao": "Dica de efeitos/legendas (Ex: Legendas grandes, zoom rápido no rosto, música de tensão)"
      }
    ]
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": MODELO_IA,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": f"Transcrição para análise de DNA viral: {transcricao}"}
                ],
                "response_format": { "type": "json_object" }
            })
        )

        if response.status_code == 200:
            resultado = response.json()
            conteudo = resultado['choices'][0]['message']['content']
            return json.loads(conteudo)
        else:
            print(f"Erro: {response.text}")
            return []

    except Exception as e:
        print(f"Erro no serviço de LLM: {str(e)}")
        return []