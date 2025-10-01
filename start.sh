#!/bin/bash

set -e  # Arrêter en cas d'erreur

echo "🚀 Démarrage du Bot API Server et du Bot de Compression..."

# Créer le dossier de travail
mkdir -p /tmp/bot-api

# Démarrer le Bot API Server en arrière-plan
echo "🔧 Démarrage du Bot API Server sur le port ${BOT_API_SERVER_PORT}..."
/usr/local/bin/telegram-bot-api \
    --local \
    --api-id="${API_ID}" \
    --api-hash="${API_HASH}" \
    --http-port="${BOT_API_SERVER_PORT}" \
    --http-host="${BOT_API_SERVER_HOST}" \
    --dir="/tmp/bot-api" \
    --log-verbosity=1 \
    --log="/tmp/bot-api/server.log" &

# Attendre que le Bot API Server soit opérationnel
echo "⏳ Attente du démarrage du Bot API Server..."
sleep 10

# Vérifier que le serveur répond
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://localhost:${BOT_API_SERVER_PORT}/health" > /dev/null; then
        echo "✅ Bot API Server démarré avec succès"
        break
    else
        echo "⏱️  Tentative $((RETRY_COUNT + 1))/$MAX_RETRIES..."
        sleep 5
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Le Bot API Server ne répond pas après $MAX_RETRIES tentatives"
    echo "📋 Logs du serveur:"
    cat /tmp/bot-api/server.log 2>/dev/null || echo "Aucun log disponible"
    exit 1
fi

# Démarrer le bot Python
echo "🤖 Démarrage du bot de compression vidéo..."
exec python3 bot.py
