#!/bin/bash

VERSIONS=(
    "v7.8.0"
    "v7.7.5" 
    "v7.7.0"
    "v7.6.0"
    "v7.5.0"
)

for version in "${VERSIONS[@]}"; do
    echo "🔍 Vérification de $version..."
    URL1="https://github.com/tdlib/telegram-bot-api/releases/download/$version/telegram-bot-api-Linux.tar.gz"
    URL2="https://github.com/tdlib/telegram-bot-api/releases/download/$version/telegram-bot-api-Linux"
    
    if curl --output /dev/null --silent --head --fail "$URL1"; then
        echo "✅ $URL1 - DISPONIBLE"
    else
        echo "❌ $URL1 - INDISPONIBLE"
    fi
    
    if curl --output /dev/null --silent --head --fail "$URL2"; then
        echo "✅ $URL2 - DISPONIBLE"
    else
        echo "❌ $URL2 - INDISPONIBLE"
    fi
    echo "---"
done
