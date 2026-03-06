# ⚡ EditMind | Copiloto Inteligente de Edição

> **Transformando vídeos brutos em conteúdo de alta retenção através de Inteligência Artificial.**

O **EditMind** é um Micro-SaaS B2B projetado para automatizar o trabalho braçal de editores de vídeo e criadores de conteúdo. Nossa arquitetura une uma interface de alta performance com um motor de processamento de mídia pesado, focando na criação de cortes otimizados para Shorts, TikTok e Reels.

---

## 🎯 O Problema que Resolvemos
A edição de "Cortes" (clipagem) exige horas de trabalho mecânico: procurar silêncios, cortar erros de fala, reenquadrar para o formato vertical (9:16) e legendar. O EditMind automatiza o fluxo mecânico, permitindo que o editor atue apenas como curador de conteúdo.

## ✨ Funcionalidades (Roadmap)

- [x] **Motor de Ingestão de Mídia:** Upload otimizado de arquivos de vídeo pesados.
- [x] **Extração Analítica:** Coleta de metadados em tempo real (Resolução, Framerate, Duração) via FFmpeg.
- [x] **Separação de Áudio:** Extração automática da trilha sonora para processamento de IA.
- [ ] **Integração Whisper AI:** Transcrição completa com *timestamps* exatos.
- [ ] **Curadoria Inteligente (Lotes):** IA que sugere os melhores cortes e ganchos de retenção.
- [ ] **Edição via Texto:** Deleção de trechos do vídeo simplesmente apagando frases na transcrição.
- [ ] **Auto-Reframe:** Enquadramento dinâmico e inteligente para o formato vertical.

## 🎨 Arquitetura de UI/UX
Desenvolvido com foco na usabilidade de editores profissionais:
* **Estética Dark Fusion:** Ambiente visual escuro (`#0b0d11`) com destaques em Laranja Neon (`#f97316`) para reduzir a fadiga visual.
* **Bento Grid:** Exibição de dados técnicos fragmentada em cartões de vidro jateado (*Glassmorphism*).
* **Fluxo Stepper:** Navegação horizontal dividida em etapas (Briefing > Upload > Curadoria > Exportação).

## 🛠️ Stack Tecnológico

**Back-end (Motor & IA):**
* `Python 3`
* `FastAPI` (APIs assíncronas de alta velocidade)
* `Uvicorn` (Servidor ASGI)
* `FFmpeg` (Processamento de vídeo e áudio)

**Front-end (Interface Visual):**
* `HTML5` / `JavaScript`
* `Tailwind CSS` (Estilização responsiva nativa)
* Hospedagem Nuvem: `Vercel`

---

## 🚀 Como rodar o projeto localmente

### Pré-requisitos
* Python 3.10+
* [FFmpeg](https://ffmpeg.org/) instalado e configurado nas Variáveis de Ambiente.

### Passo a Passo

1. **Clone o repositório:**
  
   git clone [https://github.com/seu-usuario/EditMind.git](https://github.com/seu-       usuario/EditMind.git)
   cd EditMind/backend

2.  Ative o ambiente virtual e instale as dependências:

    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Linux/Mac:
    source venv/bin/activate

    
    pip install -r requirements.txt

4.  Inicie o Servidor:
  
    uvicorn main:app --reload

    O servidor estará rodando em http://127.0.0.1:8000

    Inicie o Front-end:
    Abra o arquivo frontend/index.html no seu navegador ou utilize a extensão Live Server.


    solução frontend: https://edit-mind.vercel.app/
    
