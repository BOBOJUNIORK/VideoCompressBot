FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    cmake \
    g++ \
    libssl-dev \
    zlib1g-dev \
    unzip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Installer le Bot API Server
WORKDIR /tmp
RUN wget https://github.com/tdlib/telegram-bot-api/archive/refs/heads/master.zip -O bot-api.zip && \
    unzip -q bot-api.zip && \
    cd telegram-bot-api-master && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    cmake --build . --target install && \
    cd /tmp && rm -rf telegram-bot-api-master bot-api.zip

# Configurer l'application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

ENV BOT_API_SERVER_PORT=8081
ENV BOT_API_SERVER_HOST=0.0.0.0

EXPOSE 8081

CMD ["./start.sh"]
