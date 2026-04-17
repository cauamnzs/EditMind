import requests
import json
import re
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
NGROK_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# --- CONFIGURAÇÃO ---
MODELO_IA = "openrouter/auto"


def _ts_para_seg(ts: str) -> float:
    """Converte MM:SS ou HH:MM:SS para segundos totais."""
    partes = ts.strip().split(":")
    try:
        if len(partes) == 2:
            return int(partes[0]) * 60 + float(partes[1])
        elif len(partes) == 3:
            return int(partes[0]) * 3600 + int(partes[1]) * 60 + float(partes[2])
    except (ValueError, IndexError):
        pass
    return 0.0


def _seg_para_ts(segundos: float) -> str:
    """Converte segundos para MM:SS estrito (segundos sempre 00-59)."""
    segundos = max(0.0, segundos)
    minutos = int(segundos) // 60
    segs = int(segundos) % 60
    return f"{minutos:02d}:{segs:02d}"


def _validar_e_corrigir_cortes(cortes: List[Dict]) -> List[Dict]:
    """
    Validação pós-parse: corrige timestamps inválidos e remove sobreposições.
    Esta camada é a defesa contra alucinações do LLM.
    """
    cortes_validos = []

    for corte in cortes:
        inicio_raw = corte.get("inicio", "00:00")
        fim_raw = corte.get("fim", "00:00")

        inicio_seg = _ts_para_seg(inicio_raw)
        fim_seg = _ts_para_seg(fim_raw)

        # Corrige timestamps com segundos >= 60 (alucinação de formato)
        corte["inicio"] = _seg_para_ts(inicio_seg)
        corte["fim"] = _seg_para_ts(fim_seg)

        # Descarta corte com duração inválida ou menor que 10 segundos
        duracao = fim_seg - inicio_seg
        if duracao < 10:
            print(f"⚠️ [LLM Validator] Corte descartado (duração {duracao:.1f}s < 10s): '{corte.get('titulo')}'")
            continue

        # Verifica sobreposição com cortes já aceitos
        sobreposicao = False
        for aceito in cortes_validos:
            aceito_inicio = _ts_para_seg(aceito["inicio"])
            aceito_fim = _ts_para_seg(aceito["fim"])
            # Sobreposição se os intervalos se cruzam
            if inicio_seg < aceito_fim and fim_seg > aceito_inicio:
                print(f"⚠️ [LLM Validator] Sobreposição detectada: '{corte.get('titulo')}' overlaps '{aceito.get('titulo')}'")
                sobreposicao = True
                break

        if not sobreposicao:
            cortes_validos.append(corte)

    return cortes_validos


def sugerir_cortes(transcricao: str) -> List[Dict]:
    print("🧠 [Brain Engine] Analisando transcrição para cortes virais...")

    if not transcricao or len(transcricao.strip()) < 50:
        return []

    prompt_sistema = """
Você é o Brain Engine do EditMind, o algoritmo chefe de cortes virais para TikTok e Reels.
Sua única função é analisar transcrições e retornar os 3 melhores cortes cronologicamente distintos.

═══════════════════════════════════════════════════
🔴 REGRAS ABSOLUTAS — VIOLÁ-LAS INVALIDA A RESPOSTA
═══════════════════════════════════════════════════

REGRA 1 — EXCLUSIVIDADE CRONOLÓGICA (ANTI-OVERLAP):
Os 3 cortes DEVEM ser cronologicamente separados. Os intervalos [inicio, fim] NÃO podem se sobrepor.
Se o Corte 1 usa 00:10-00:40, os Cortes 2 e 3 DEVEM começar DEPOIS de 00:40.
Pense no vídeo como uma linha do tempo dividida em 3 zonas distintas: começo, meio e fim.

REGRA 2 — FORMATO DE TEMPO ESTRITO (MM:SS):
Os valores de "inicio" e "fim" devem estar no formato MM:SS onde SS é sempre entre 00 e 59.
Se um momento ocorre nos 65 segundos do vídeo: escreva 01:05, NUNCA 00:65.
Se um momento ocorre nos 90 segundos: escreva 01:30, NUNCA 00:90 ou 01:90.
Regra de ouro: quando os segundos chegarem a 60, incremente o minuto.

REGRA 3 — VARIEDADE DE GATILHOS EMOCIONAIS:
Cada corte deve explorar um gatilho psicológico DIFERENTE:
- Corte 1 → PATHOS: Apelo emocional, história pessoal, dor/desejo do espectador.
- Corte 2 → LOGOS: Dado surpreendente, insight contraintuitivo, prova lógica.
- Corte 3 → ETHOS: Autoridade, credibilidade, prova social ou resultado concreto.
O campo "motivo" deve identificar explicitamente qual gatilho foi usado e por quê.

REGRA 4 — DURAÇÃO MÍNIMA E MÁXIMA:
Cada corte deve ter duração entre 15 e 90 segundos. Cortes fora desse range são inválidos.

═══════════════════════════════════════════════════
📦 FORMATO DE SAÍDA OBRIGATÓRIO
═══════════════════════════════════════════════════

Retorne APENAS um Array JSON válido. Sem markdown, sem explicações, sem texto antes ou depois.
[
  {
    "titulo": "Título curto e impactante (máx 6 palavras)",
    "viral_score": 95,
    "inicio": "00:10",
    "fim": "00:45",
    "gancho": "Frase exata dita nos primeiros 3 segundos que prende atenção",
    "motivo": "PATHOS — Explica o gatilho emocional explorado e por que viraliza",
    "texto_corte": "Transcrição exata e completa de todo o conteúdo falado neste trecho.",
    "keyword_broll": "single_english_word"
  },
  { ... Corte 2 com inicio APÓS o fim do Corte 1 ... },
  { ... Corte 3 com inicio APÓS o fim do Corte 2 ... }
]

O viral_score é um inteiro de 70 a 99 baseado no potencial de viralização.
A keyword_broll é UMA palavra em inglês (ex: money, success, gym, food).
"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": NGROK_URL,
                "X-Title": "EditMind Brain Engine"
            },
            data=json.dumps({
                "model": MODELO_IA,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": f"Transcrição para análise:\n\n{transcricao}"}
                ],
                "temperature": 0.3
            }),
            timeout=60
        )

        if response.status_code != 200:
            print(f"❌ [Brain Engine] HTTP {response.status_code}: {response.text[:200]}")
            return []

        resultado = response.json()
        conteudo_texto = resultado['choices'][0]['message']['content']
        print(f"📝 [Brain Engine] Resposta bruta recebida ({len(conteudo_texto)} chars)")

        match = re.search(r'\[.*\]', conteudo_texto, re.DOTALL)
        if not match:
            print("❌ [Brain Engine] JSON Array não encontrado na resposta do LLM")
            return []

        cortes_brutos = json.loads(match.group(0))
        cortes_validados = _validar_e_corrigir_cortes(cortes_brutos)

        print(f"✅ [Brain Engine] {len(cortes_validados)}/{len(cortes_brutos)} cortes validados")
        return cortes_validados

    except json.JSONDecodeError as e:
        print(f"❌ [Brain Engine] JSON inválido na resposta do LLM: {e}")
        return []
    except Exception as e:
        print(f"❌ [Brain Engine] Erro inesperado: {str(e)}")
        return []


def extrair_keyword_broll(texto_corte: str) -> str:
    """
    Extrai palavra-chave para B-Roll usando IA.
    Fallback caso o LLM principal não retorne keyword.
    """
    if not texto_corte or len(texto_corte.strip()) < 10:
        return "abstract"
    
    prompt = f"""
    Analise este trecho de vídeo e retorne APENAS uma única palavra-chave em inglês
    para buscar uma imagem/stock photo relacionada ao tema. Retorne apenas a palavra,
    sem explicações.
    
    Trecho: {texto_corte[:200]}
    """
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": NGROK_URL,
                "X-Title": "EditMind B-Roll"
            },
            data=json.dumps({
                "model": MODELO_IA,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }),
            timeout=30
        )
        
        if response.status_code == 200:
            resultado = response.json()
            keyword = resultado['choices'][0]['message']['content'].strip().lower()
            # Remove pontuação e espaços
            keyword = re.sub(r'[^a-z]', '', keyword)
            return keyword if keyword else "abstract"
        return "abstract"
    except Exception as e:
        print(f" Erro extraindo keyword B-Roll: {e}")
        return "abstract"