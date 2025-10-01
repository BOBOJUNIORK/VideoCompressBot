# VideoCompressBot Pro 🎬

Bot Telegram de compression vidéo avancé avec support des fichiers jusqu'à 2GB via Bot API Server.

## 🚀 Fonctionnalités

- ✅ Compression multi-résolution (360p, 480p, 720p, 1080p)
- ✅ Support des fichiers jusqu'à 2GB
- ✅ Bot API Server intégré
- ✅ Optimisé pour Railway/Docker
- ✅ Nettoyage automatique des fichiers temporaires

## 🛠️ Installation

### Variables d'environnement requises:

```env
BOT_TOKEN=votre_token_bot
API_ID=votre_api_id_telegram
API_HASH=votre_api_hash_telegram

## Déploiement Railway:

- Forkez ce repository
- Déployez sur Railway
- Configurez les variables d'environnement
- C'est parti ! 🎉

### Déploiement local:
docker-compose up -d

## 📊 Résolutions supportées

- 360p (640x360)
- 480p (854x480)
- 720p (1280x720)
- 1080p (1920x1080)

## 🔧 Technologies

- Python 3.11
- Telegram Bot API Server
- FFmpeg
- Docker
- Railway
