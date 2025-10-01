FROM python:3.11-slim

# Installer les dépendances de compilation
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    cmake \
    g++ \
    libssl-dev \
    zlib1g-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Cloner et compiler le Bot API Server depuis les sources
WORKDIR /tmp
RUN git clone https://github.com/tdlib/td.git && \
    cd td && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    cmake --build . --target prepare_cross_compiling && \
    cd .. && mkdir build2 && cd build2 && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    cmake --build . --target telegram-bot-api && \
    cp bin/telegram-bot-api /usr/local/bin/ && \
    chmod +x /usr/local/bin/telegram-bot-api && \
    cd /tmp && rm -rf td

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

ENV BOT_API_SERVER_PORT=8081
ENV BOT_API_SERVER_HOST=0.0.0.0

EXPOSE 8081

CMD ["./start.sh"]