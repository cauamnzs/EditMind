# ==========================================
# EditMind API — Dockerfile para Render.com
# ==========================================

# Imagem base Python slim
FROM python:3.10-slim

# Instala FFmpeg e dependências de sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libgomp1 \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Define pasta de trabalho
WORKDIR /app

# Copia e instala dependências Python primeiro (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Cria pastas de upload necessárias
RUN mkdir -p uploads/videos uploads/audios uploads/cortes uploads/temp_clips uploads/broll

# Expõe porta (o Render injeta $PORT automaticamente)
EXPOSE ${PORT:-8000}

# Comando de inicialização
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
