FROM python:3.11-slim

# Installer les dépendances
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Télécharger le binaire avec vérification
RUN echo "📥 Téléchargement du Bot API Server..." && \
    wget --progress=dot:giga -O /usr/local/bin/telegram-bot-api \
    "https://github.com/tdlib/telegram-bot-api/releases/download/v7.8.0/telegram-bot-api-Linux" && \
    chmod +x /usr/local/bin/telegram-bot-api

# Vérifier que le binaire fonctionne
RUN echo "🔍 Vérification de l'installation..." && \
    /usr/local/bin/telegram-bot-api --version && \
    echo "✅ Bot API Server installé avec succès"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

ENV BOT_API_SERVER_PORT=8081
ENV BOT_API_SERVER_HOST=0.0.0.0

EXPOSE 8081

CMD ["./start.sh"]
