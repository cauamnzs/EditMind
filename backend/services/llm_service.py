def sugerir_cortes(texto_transcricao: str) -> dict:
    """
    MODO DESENVOLVEDOR (MOCK):
    Simula a resposta da IA para testes locais sem gastar cota de API.
    """
    print("[LLM] MODO DEV ATIVADO: Simulando a Inteligência Artificial (Custo Zero!)...")

    # A gente devolve um JSON perfeito e fixo para o Front-end poder testar a tela
    corte_simulado = {
        "inicio": "00:03",
        "fim": "00:15",
        "motivo": "Trecho simulado: Contém o gancho principal e o pico de retenção do vídeo."
    }
    
    return corte_simulado