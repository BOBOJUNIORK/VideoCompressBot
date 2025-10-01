#!/bin/bash

echo "🚀 Démarrage du Bot API Server et du Bot de Compression..."

# Démarrer le Bot API Server en arrière-plan
echo "🔧 Démarrage du Bot API Server sur le port ${BOT_API_SERVER_PORT}..."
/usr/local/bin/telegram-bot-api \
    --local \
    --api-id="${API_ID}" \
    --api-hash="${API_HASH}" \
    --http-port="${BOT_API_SERVER_PORT}" \
    --http-host="${BOT_API_SERVER_HOST}" \
    --dir="/tmp/bot-api" \
    --log="/tmp/bot-api/server.log" &

# Attendre que le Bot API Server soit opérationnel
echo "⏳ Attente du démarrage du Bot API Server..."
sleep 15

# Vérifier que le serveur répond
if curl -s http://localhost:${BOT_API_SERVER_PORT}/health > /dev/null; then
    echo "✅ Bot API Server démarré avec succès"
else
    echo "❌ Le Bot API Server ne répond pas, vérifiez les logs"
    exit 1
fi

# Démarrer le bot Python
echo "🤖 Démarrage du bot de compression vidéo..."
python3 bot.py
