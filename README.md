# ⚡ EditMind | Creator Copilot

> **Transformando vídeos brutos em conteúdo de alta retenção através de Inteligência Artificial.**

O **EditMind** é um Micro-SaaS B2B projetado para automatizar o trabalho braçal de editores de vídeo e criadores de conteúdo. Nossa arquitetura une uma interface de alta performance com um motor de processamento de mídia pesado, focando na criação de cortes otimizados para Shorts, TikTok e Reels.

---

## 🎯 O Problema que Resolvemos
A edição de "Cortes" (clipagem) exige horas de trabalho mecânico: baixar vídeos pesados, procurar silêncios, cortar erros de fala, reenquadrar para o formato vertical (9:16) e legendar. O EditMind automatiza o fluxo mecânico, permitindo que o editor atue apenas como curador de conteúdo.

## ✨ Funcionalidades (Roadmap & Status)

- [x] **Motor de Ingestão de Mídia:** Upload otimizado de arquivos de vídeo pesados.
- [x] **YouTube Downloader Integrado:** Extração direta de vídeos e podcasts do YouTube em altíssima qualidade (1080p+) direto para o servidor.
- [x] **Extração Analítica:** Coleta de metadados em tempo real (Resolução, Framerate, Duração) via FFmpeg.
- [x] **Separação de Áudio:** Extração automática da trilha sonora (MP3) para processamento de IA.
- [ ] **Integração Whisper AI:** Transcrição completa com *timestamps* exatos.
- [ ] **Curadoria Inteligente (Lotes):** IA que sugere os melhores cortes e ganchos de retenção.
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
   
  * git clone [https://github.com/seu-usuario/EditMind.git](https://github.com/seu-usuario/EditMind.git)
  * cd EditMind/backend

   **Ative o ambiente virtual e instale as dependências:**
   

 * python -m venv venv
    # Windows:
 * venv\Scripts\activate
    # Linux/Mac:
 * source venv/bin/activate

 * pip install -r requirements.txt

   **Inicie o Servidor Backend:**
    
  * uvicorn main:app --reload