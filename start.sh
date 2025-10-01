#!/bin/bash

set -e

echo "🚀 Démarrage du Bot API Server et du Bot de Compression..."

# Vérifier Python
echo "✅ Python version: $(python --version)"

# Démarrer le Bot API Server
mkdir -p /tmp/bot-api

echo "🔧 Démarrage du Bot API Server..."
/usr/local/bin/telegram-bot-api \
    --local \
    --api-id="${API_ID}" \
    --api-hash="${API_HASH}" \
    --http-port="${BOT_API_SERVER_PORT}" \
    --http-host="${BOT_API_SERVER_HOST}" \
    --dir="/tmp/bot-api" \
    --log-verbosity=1 \
    --log="/tmp/bot-api/server.log" &

echo "⏳ Attente du démarrage..."
sleep 15

# Vérification
MAX_RETRIES=10
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s "http://localhost:${BOT_API_SERVER_PORT}/health" > /dev/null; then
        echo "✅ Bot API Server démarré"
        break
    fi
    echo "⏱️  Tentative $i/$MAX_RETRIES..."
    sleep 5
done

echo "🤖 Démarrage du bot..."
exec python bot.py
