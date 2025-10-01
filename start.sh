#!/bin/bash

set -e

echo "🚀 Démarrage du système..."

# Vérifier les dépendances
echo "🔍 Vérification des dépendances..."
command -v ffmpeg >/dev/null 2>&1 || { echo "❌ FFmpeg non trouvé"; exit 1; }
command -v python >/dev/null 2>&1 || { echo "❌ Python non trouvé"; exit 1; }
command -v telegram-bot-api >/dev/null 2>&1 || { echo "❌ Bot API Server non trouvé"; exit 1; }

echo "✅ Toutes les dépendances sont disponibles"

# Préparer l'environnement
mkdir -p /tmp/bot-api

# Démarrer le Bot API Server
echo "🔧 Démarrage du Bot API Server..."
telegram-bot-api \
    --local \
    --api-id="${API_ID}" \
    --api-hash="${API_HASH}" \
    --http-port="${BOT_API_SERVER_PORT}" \
    --http-host="${BOT_API_SERVER_HOST}" \
    --dir="/tmp/bot-api" \
    --log-verbosity=1 \
    --log="/tmp/bot-api/server.log" &

# Attendre le démarrage
echo "⏳ Attente du démarrage du serveur..."
sleep 10

# Vérifier que le serveur répond
MAX_RETRIES=15
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s "http://localhost:${BOT_API_SERVER_PORT}/health" > /dev/null; then
        echo "✅ Bot API Server opérationnel"
        break
    fi
    echo "⏱️  Tentative $i/$MAX_RETRIES..."
    sleep 3
done

# Démarrer le bot
echo "🤖 Démarrage du bot de compression..."
exec python bot.py
