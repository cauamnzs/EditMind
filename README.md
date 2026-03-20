# ⚡ EditMind | Creator Copilot

> **Transformando vídeos brutos em conteúdo de alta retenção através de Inteligência Artificial.**

O **EditMind** é um Micro-SaaS B2B projetado para automatizar o trabalho braçal de editores de vídeo e criadores de conteúdo. Nossa arquitetura une uma interface de alta performance com um motor de processamento de mídia pesado, focando na criação de cortes otimizados para Shorts, TikTok e Reels.

---

## 🎯 O Problema que Resolvemos
A edição de "Cortes" (clipagem) exige horas de trabalho mecânico: baixar vídeos pesados, procurar silêncios, cortar erros de fala, reenquadrar para o formato vertical (9:16) e legendar. O EditMind automatiza o fluxo mecânico, permitindo que o editor atue apenas como curador de conteúdo.

## ✨ Funcionalidades (Roadmap & Status)

- [x] **Motor de Ingestão de Mídia:** Upload otimizado de arquivos de vídeo via Drag & Drop.
- [x] **YouTube Downloader Integrado:** Extração direta de vídeos e podcasts do YouTube em altíssima qualidade (1080p+) direto para o servidor.
- [x] **Extração Analítica:** Coleta de metadados em tempo real (Resolução, Framerate, Duração) via FFmpeg.
- [x] **Painel de Controle Responsivo:** Layout fluido e adaptável do Mobile ao Desktop (Bento Grid).
- [x] **Landing Page Institucional:** Página de vendas de alta conversão integrada ao fluxo do app.
- [x] **Calibração de IA:** Sistema para definição do tempo alvo do corte (30s, 60s ou 120s).
- [x] **Curadoria Inteligente (Lotes):** IA integrada que analisa, transcreve e já sugere os melhores ganchos e minutos exatos de retenção.
- [ ] **Renderização do Vídeo Final:** Processamento e reenquadramento automático (9:16) no player com base nas sugestões da IA.
- [ ] **Edição via Texto:** Deleção de trechos do vídeo apagando frases na transcrição.

## 🎨 Arquitetura de UI/UX
Desenvolvido com foco na usabilidade de editores profissionais:
* **Dashboard Moderno:** Navegação em SPA (Single Page Application) com um *Floating Dock* inferior para transição suave entre ferramentas.
* **Estética Dark Fusion:** Ambiente visual escuro (`#0b0d11`) com destaques em Laranja Neon (`#f97316`) e interações baseadas em luzes difusas.
* **Bento Grid:** Exibição de dados técnicos fragmentada em cartões de vidro jateado (*Glassmorphism*).

## 🛠️ Stack Tecnológico

**Back-end (Motor & Extração):**
* `Python 3`
* `FastAPI` (APIs assíncronas de alta velocidade)
* `Uvicorn` (Servidor ASGI)
* `FFmpeg` (Processamento de vídeo e áudio)
* `yt-dlp` (Extração de mídias de rede)

**Front-end (Interface Visual):**
* `HTML5` / `JavaScript Vanilla`
* `Tailwind CSS` (Estilização responsiva nativa)
* Hospedagem Nuvem: `Vercel`

---

## 🚀 Como rodar o projeto localmente

### Pré-requisitos
* Python 3.10+
* [FFmpeg](https://ffmpeg.org/) instalado e configurado nas Variáveis de Ambiente do Sistema (Windows/Linux/Mac).

### Passo a Passo

1. **Clone o repositório:**
```bash
git clone [https://github.com/seu-usuario/EditMind.git](https://github.com/seu-usuario/EditMind.git)
cd EditMind/backend

2.   **Ative o ambiente virtual e instale as dependências:**
   

 * python -m venv venv
    # Windows:
 * venv\Scripts\activate
    # Linux/Mac:
 * source venv/bin/activate

 * pip install -r requirements.txt

3.   **Inicie o Servidor Backend:**
    
    pip install -r requirements.txt

4.  Inicie o Servidor:
  
    uvicorn main:app --reload

    O servidor estará rodando em http://127.0.0.1:8000

    Inicie o Front-end:
    Abra o arquivo frontend/index.html no seu navegador ou utilize a extensão Live Server.


    solução frontend: https://edit-mind.vercel.app/
    
