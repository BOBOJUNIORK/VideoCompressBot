FROM python:3.11-slim

# Installer les dépendances
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Télécharger depuis le bon dépôt et la bonne version
RUN wget -O /usr/local/bin/telegram-bot-api \
    "https://github.com/tdlib/telegram-bot-api/releases/download/v1.8.0/telegram-bot-api" && \
    chmod +x /usr/local/bin/telegram-bot-api

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

ENV BOT_API_SERVER_PORT=8081
ENV BOT_API_SERVER_HOST=0.0.0.0

EXPOSE 8081

CMD ["./start.sh"]