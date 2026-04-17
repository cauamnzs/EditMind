import requests
import json
import re
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
NGROK_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

MODELO_IA = "openrouter/auto"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Session HTTP persistente — reutiliza conexão TCP entre chamadas
_http_session = requests.Session()
_http_session.headers.update({
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": NGROK_URL,
    "X-Title": "EditMind Brain Engine",
})


def _chamar_openrouter(
    mensagens: List[Dict],
    temperature: float = 0.2,
    max_tokens: int = 8000,
    timeout: int = 120,
) -> Optional[str]:
    """Helper centralizado para chamadas ao OpenRouter. Retorna o texto da resposta ou None."""
    try:
        resp = _http_session.post(
            _OPENROUTER_URL,
            data=json.dumps({
                "model": MODELO_IA,
                "messages": mensagens,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }),
            timeout=timeout,
        )
        if resp.status_code != 200:
            print(f"[OpenRouter] HTTP {resp.status_code}: {resp.text[:300]}")
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[OpenRouter] Erro na chamada: {e}")
        return None


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
            print(f" [LLM Validator] Corte descartado (duração {duracao:.1f}s < 10s): '{corte.get('titulo')}'")
            continue

        # Verifica sobreposição com cortes já aceitos
        sobreposicao = False
        for aceito in cortes_validos:
            aceito_inicio = _ts_para_seg(aceito["inicio"])
            aceito_fim = _ts_para_seg(aceito["fim"])
            # Sobreposição se os intervalos se cruzam
            if inicio_seg < aceito_fim and fim_seg > aceito_inicio:
                print(f" [LLM Validator] Sobreposição detectada: '{corte.get('titulo')}' overlaps '{aceito.get('titulo')}'")
                sobreposicao = True
                break

        if not sobreposicao:
            cortes_validos.append(corte)

    return cortes_validos


def sugerir_cortes(transcricao: str) -> List[Dict]:
    print(" [Brain Engine] Analisando transcrição para cortes virais...")

    if not transcricao or len(transcricao.strip()) < 50:
        return []

    prompt_sistema = """
Você é o Brain Engine do EditMind, o algoritmo chefe de cortes virais para TikTok e Reels.
Sua única função é analisar transcrições e retornar os 3 melhores cortes cronologicamente distintos.

═══════════════════════════════════════════════════════════════════
🔴 REGRAS ABSOLUTAS — VIOLÁ-LAS INVALIDA A RESPOSTA
═══════════════════════════════════════════════════════════════════

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

═══════════════════════════════════════════════════════════════════
📦 FORMATO DE SAÍDA OBRIGATÓRIO
═══════════════════════════════════════════════════════════════════

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

    conteudo_texto = _chamar_openrouter(
        mensagens=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Transcrição para análise:\n\n{transcricao}"}
        ],
        temperature=0.3,
        max_tokens=4000,
        timeout=60,
    )
    if not conteudo_texto:
        return []

    try:
        print(f"[Brain Engine] Resposta: {len(conteudo_texto)} chars")
        match = re.search(r'\[.*\]', conteudo_texto, re.DOTALL)
        if not match:
            print("[Brain Engine] JSON Array não encontrado")
            return []
        cortes_brutos = json.loads(match.group(0))
        cortes_validados = _validar_e_corrigir_cortes(cortes_brutos)
        print(f"[Brain Engine] {len(cortes_validados)}/{len(cortes_brutos)} cortes validados")
        return cortes_validados
    except json.JSONDecodeError as e:
        print(f"[Brain Engine] JSON inválido: {e}")
        return []
    except Exception as e:
        print(f"[Brain Engine] Erro: {e}")
        return []


def _formatar_transcricao_timestamps(segmentos: List[Dict], limite_chars: int = 24000) -> str:
    """
    Converte segmentos Whisper [{start, end, text, words}] em texto formatado
    para o LLM Editor Chefe. Usa word-level timestamps para máxima precisão.
    Distribui o limite_chars proporcionalmente ao longo do vÃ­deo para nÃ£o
    cortar só o começo em vídeos longos.
    """
    linhas = []
    for seg in segmentos:
        inicio = f"{seg['start']:.3f}"
        fim    = f"{seg['end']:.3f}"
        texto  = seg.get("text", "").strip()
        if not texto:
            continue
        words = seg.get("words", [])
        if words:
            word_str = " ".join(
                f"[{w['start']:.2f}]{w['word'].strip()}" for w in words
            )
            linhas.append(f"[{inicio}-{fim}] {word_str}")
        else:
            linhas.append(f"[{inicio}-{fim}] {texto}")

    resultado_completo = "\n".join(linhas)
    if len(resultado_completo) <= limite_chars:
        return resultado_completo

    # Para vídeos longos: amostra distribuída em 3 janelas (início, meio, fim)
    # para cobrir todo o conteúdo, não só os primeiros minutos
    janela = limite_chars // 3
    total = len(resultado_completo)
    parte_inicio = resultado_completo[:janela]
    meio_start   = (total // 2) - (janela // 2)
    parte_meio   = resultado_completo[meio_start: meio_start + janela]
    parte_fim    = resultado_completo[total - janela:]
    return parte_inicio + "\n[...]\n" + parte_meio + "\n[...]\n" + parte_fim


def analisar_cortes_virais(
    segmentos: List[Dict],
    duracao_total: float,
    tempo_alvo: int = 60
) -> List[Dict]:
    """
    Editor Chefe SÃªnior: analisa transcriÃ§Ã£o com timestamps word-level e
    retorna cortes com segments_to_keep (jump-cuts internos) e synced_transcript.

    Args:
        segmentos: saÃ­da de whisper_service.transcrever_com_timestamps()
        duracao_total: duraÃ§Ã£o do vÃ­deo bruto em segundos
        tempo_alvo: duraÃ§Ã£o alvo de cada clipe (30, 60 ou 120)

    Returns:
        Lista de dicts com estrutura completa de cada corte viral.
    """
    print(f"🎬 [Brain Engine v2] Analisando {len(segmentos)} segmentos Whisper...")

    if not segmentos:
        return []

    transcricao_formatada = _formatar_transcricao_timestamps(segmentos)

    # Calcula número de cortes: 1 corte a cada ~90s de conteúdo (mín 3, máx 12)
    n_cortes = max(3, min(12, int(duracao_total // max(tempo_alvo * 1.5, 90))))

    prompt_sistema = f"""
Você é o Editor Chefe Sênior do EditMind, especialista em retenção para TikTok, Reels e YouTube Shorts.
Sua obsessão: eliminar tempo morto e criar múltiplos vídeos únicos e dinâmicos a partir de um bruto.

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
ðŸ”´ MISSÃƒO
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

A transcrição abaixo contém timestamps word-level no formato:
[START-END] [tempo]palavra [tempo]palavra...

Exemplo: [12.500-18.200] [12.5]Fala [12.9]galera, [13.4]hoje...

Você deve retornar EXATAMENTE {n_cortes} cortes virais únicos, cada um com:

1. SEGMENTO BRUTO: os timestamps exatos de início e fim do trecho no vídeo original (HH:MM:SS.mmm)
2. SEGMENTS_TO_KEEP: lista de sub-segmentos dentro do trecho onde há fala útil.
   - REMOVE silêncios > 0.3s
   - REMOVE vícios de linguagem ("é...", "tipo...", "né...", pausas longas)
   - REMOVE gaguejos (palavras repetidas como "eu eu eu")
   - Cada entrada é {{"start": float_segundos, "end": float_segundos}}
   - Os valores são em segundos absolutos do vídeo ORIGINAL
3. SYNCED_TRANSCRIPT: legendas recalculadas para a timeline EDITADA do clipe.
   - start_offset e end_offset são relativos ao início do clipe (0.0 = primeiro frame do clipe)
   - Máximo 4 palavras por entrada para efeito karaoke
   - Os offsets devem bater exatamente com a fala após os cortes

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
ðŸ”´ REGRAS ABSOLUTAS
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

REGRA 1 — EXCLUSIVIDADE: Nenhum corte pode sobrepor timestamps de outro.
REGRA 2 — DURAÇÃO: Cada clipe editado (sum dos segments_to_keep) deve ter entre 15s e {min(90, tempo_alvo)}s.
REGRA 3 — GANCHOS ÚNICOS: Cada corte deve ter gancho emocional distinto (PATHOS/LOGOS/ETHOS).
REGRA 4 — FORMATO DE TEMPO: Use float seconds (ex: 125.340) para segments_to_keep.
           Use HH:MM:SS.mmm para raw_start/raw_end.
REGRA 5 — VARIEDADE: Cada corte aborda um sub-tópico diferente do bruto.

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
ðŸ“¦ FORMATO DE SAÃDA OBRIGATÃ“RIO (JSON puro, sem markdown)
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

[
  {{
    "cut_id": 1,
    "titulo": "Título impactante máx 6 palavras",
    "viral_score": 95,
    "gancho": "Frase exata dos primeiros 3s que prende atenção",
    "motivo": "PATHOS — por que viraliza",
    "keyword_broll": "single_english_word",
    "raw_start": "HH:MM:SS.mmm",
    "raw_end": "HH:MM:SS.mmm",
    "segments_to_keep": [
      {{"start": 70.200, "end": 75.800}},
      {{"start": 76.900, "end": 82.100}},
      {{"start": 83.400, "end": 91.000}}
    ],
    "synced_transcript": [
      {{"start_offset": 0.0,  "end_offset": 1.5,  "text": "Fala galera beleza"}},
      {{"start_offset": 1.5,  "end_offset": 3.2,  "text": "hoje vou mostrar"}},
      {{"start_offset": 3.2,  "end_offset": 5.8,  "text": "o segredo que ninguÃ©m"}}
    ]
  }}
]

Retorne APENAS o array JSON. Sem explicaÃ§Ãµes. Sem markdown.
"""

    conteudo = _chamar_openrouter(
        mensagens=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"TranscriÃ§Ã£o com timestamps (duraÃ§Ã£o total: {duracao_total:.1f}s):\n\n{transcricao_formatada}"}
        ],
        temperature=0.2,
        max_tokens=8000,
        timeout=120,
    )
    if not conteudo:
        return []

    try:
        print(f"[Brain Engine v2] Resposta: {len(conteudo)} chars")
        match = re.search(r'\[.*\]', conteudo, re.DOTALL)
        if not match:
            print("[Brain Engine v2] Array JSON nÃ£o encontrado")
            return []
        cortes_brutos = json.loads(match.group(0))
        cortes_validados = _validar_cortes_virais(cortes_brutos)
        print(f"[Brain Engine v2] {len(cortes_validados)}/{len(cortes_brutos)} cortes validados")
        return cortes_validados
    except json.JSONDecodeError as e:
        print(f"[Brain Engine v2] JSON invÃ¡lido: {e}")
        return []
    except Exception as e:
        print(f"[Brain Engine v2] Erro: {e}")
        return []


def _validar_cortes_virais(cortes: List[Dict]) -> List[Dict]:
    """
    Valida estrutura do JSON Editor Chefe:
    - Verifica segments_to_keep presentes e ordenados
    - Calcula duraÃ§Ã£o editada real (soma dos segmentos)
    - Remove cortes com duraÃ§Ã£o < 10s ou > 180s
    - Remove sobreposiÃ§Ãµes no raw_start/raw_end
    - Recalcula synced_transcript se offsets faltarem
    """
    validados = []

    for corte in cortes:
        segs = corte.get("segments_to_keep", [])
        if not segs:
            print(f"âš ï¸ [Validator] Corte '{corte.get('titulo')}' sem segments_to_keep â€” descartado")
            continue

        # Ordena segmentos por start
        segs_sorted = sorted(segs, key=lambda s: float(s.get("start", 0)))
        corte["segments_to_keep"] = segs_sorted

        # Calcula duraÃ§Ã£o editada
        duracao_editada = sum(
            float(s["end"]) - float(s["start"])
            for s in segs_sorted
            if float(s.get("end", 0)) > float(s.get("start", 0))
        )
        corte["final_edited_duration_seconds"] = round(duracao_editada, 2)

        if duracao_editada < 10:
            print(f"âš ï¸ [Validator] Corte '{corte.get('titulo')}' muito curto ({duracao_editada:.1f}s) â€” descartado")
            continue
        if duracao_editada > 180:
            print(f"âš ï¸ [Validator] Corte '{corte.get('titulo')}' muito longo ({duracao_editada:.1f}s) â€” descartado")
            continue

        # Verifica sobreposiÃ§Ã£o de raw_start/raw_end com cortes jÃ¡ aceitos
        raw_start_s = _parse_hms(corte.get("raw_start", "0"))
        raw_end_s   = _parse_hms(corte.get("raw_end", "0"))

        sobreposicao = False
        for aceito in validados:
            a_start = _parse_hms(aceito.get("raw_start", "0"))
            a_end   = _parse_hms(aceito.get("raw_end", "0"))
            if raw_start_s < a_end and raw_end_s > a_start:
                print(f"âš ï¸ [Validator] SobreposiÃ§Ã£o: '{corte.get('titulo')}' â€” descartado")
                sobreposicao = True
                break

        if not sobreposicao:
            # Garante campos obrigatÃ³rios para compatibilidade com frontend antigo
            corte.setdefault("inicio", _seg_para_ts(raw_start_s))
            corte.setdefault("fim",    _seg_para_ts(raw_end_s))
            corte.setdefault("viral_score", corte.get("viral_score", 80))
            corte.setdefault("texto_corte", " ".join(
                s.get("text", "") for s in corte.get("synced_transcript", [])
            ))
            validados.append(corte)

    return validados


def _parse_hms(ts: str) -> float:
    """Converte HH:MM:SS.mmm ou MM:SS ou float string para segundos."""
    if not ts:
        return 0.0
    ts = str(ts).strip()
    # Tenta float direto
    try:
        return float(ts)
    except ValueError:
        pass
    # HH:MM:SS.mmm ou HH:MM:SS
    partes = ts.replace(",", ".").split(":")
    try:
        if len(partes) == 3:
            h, m, s = partes
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(partes) == 2:
            m, s = partes
            return int(m) * 60 + float(s)
    except (ValueError, IndexError):
        pass
    return 0.0


def extrair_keyword_broll(texto_corte: str) -> str:
    """
    Extrai palavra-chave para B-Roll usando IA.
    Fallback caso o LLM principal nÃ£o retorne keyword.
    """
    if not texto_corte or len(texto_corte.strip()) < 10:
        return "abstract"
    
    prompt = f"""
    Analise este trecho de vÃ­deo e retorne APENAS uma Ãºnica palavra-chave em inglÃªs
    para buscar uma imagem/stock photo relacionada ao tema. Retorne apenas a palavra,
    sem explicaÃ§Ãµes.
    
    Trecho: {texto_corte[:200]}
    """
    
    conteudo = _chamar_openrouter(
        mensagens=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=20,
        timeout=30,
    )
    if not conteudo:
        return "abstract"
    keyword = re.sub(r'[^a-z]', '', conteudo.strip().lower())
    return keyword if keyword else "abstract"
