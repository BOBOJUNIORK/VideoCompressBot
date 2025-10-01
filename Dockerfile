FROM python:3.11-slim

# Installer les dépendances
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Télécharger et installer le binaire précompilé
RUN wget -O telegram-bot-api.tar.gz "https://github.com/tdlib/telegram-bot-api/releases/download/v7.8.0/telegram-bot-api_Linux_x86_64.tar.gz" && \
    tar -xzf telegram-bot-api.tar.gz && \
    mv telegram-bot-api /usr/local/bin/ && \
    chmod +x /usr/local/bin/telegram-bot-api && \
    rm telegram-bot-api.tar.gz

# Vérifier l'installation
RUN telegram-bot-api --version

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

ENV BOT_API_SERVER_PORT=8081
ENV BOT_API_SERVER_HOST=0.0.0.0

EXPOSE 8081

CMD ["./start.sh"]
