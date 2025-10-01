FROM ubuntu:22.04

# Éviter les prompts interactifs
ENV DEBIAN_FRONTEND=noninteractive

# Installer les dépendances système (AJOUT de unzip)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    cmake \
    g++ \
    libssl-dev \
    zlib1g-dev \
    unzip \  # ⬅️ AJOUT CRITIQUE
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Installer le Bot API Server
WORKDIR /tmp
RUN wget https://github.com/tdlib/telegram-bot-api/archive/refs/heads/master.zip -O bot-api.zip && \
    unzip bot-api.zip && \
    cd telegram-bot-api-master && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    cmake --build . --target install && \
    cd /tmp && rm -rf telegram-bot-api-master bot-api.zip

# Après l'installation, vérifier que tout est en place
RUN echo "✅ Vérification des binaires installés..." && \
    which ffmpeg && ffmpeg -version | head -1 && \
    which telegram-bot-api && telegram-bot-api --version && \
    which python3 && python3 --version && \
    echo "✅ Toutes les dépendances sont installées"

# Configurer l'application
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

# Donner les permissions d'exécution
RUN chmod +x start.sh

# Variables d'environnement pour le Bot API Server
ENV BOT_API_SERVER_PORT=8081
ENV BOT_API_SERVER_HOST=0.0.0.0

# Exposer le port du Bot API Server
EXPOSE 8081

CMD ["./start.sh"]
