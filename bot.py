import os
import subprocess
import asyncio
import logging
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackContext
from telegram.request import HTTPXRequest

# === CONFIGURATION AVEC BOT API SERVER ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Configuration Bot API Server
BOT_API_SERVER = os.getenv("BOT_API_SERVER", "http://localhost:8081")
MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2GB maintenant supportés!

# Vérifications critiques
if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("❌ Variables manquantes: BOT_TOKEN, API_ID, API_HASH")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dossiers
OUTPUT_DIR = "/tmp/output_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Résolutions optimisées
RESOLUTIONS = {
    "360p": {"scale": "640x360", "crf": "26", "video_bitrate": "800k", "audio_bitrate": "96k"},
    "480p": {"scale": "854x480", "crf": "25", "video_bitrate": "1200k", "audio_bitrate": "128k"},
    "720p": {"scale": "1280x720", "crf": "23", "video_bitrate": "2500k", "audio_bitrate": "128k"},
    "1080p": {"scale": "1920x1080", "crf": "21", "video_bitrate": "5000k", "audio_bitrate": "192k"}
}

def check_ffmpeg():
    """Vérifie FFmpeg"""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        logger.info("✅ FFmpeg détecté")
        return True
    except Exception as e:
        logger.error(f"❌ FFmpeg non trouvé: {e}")
        return False

async def compress_video_resolution(input_path: str, resolution: str, message, user_id: int):
    """Compresse une vidéo dans une résolution spécifique"""
    res_config = RESOLUTIONS[resolution]
    output_path = f"/tmp/compressed_{user_id}_{resolution}.mp4"
    
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"scale={res_config['scale']}",
            "-c:v", "libx264",
            "-crf", res_config["crf"],
            "-b:v", res_config["video_bitrate"],
            "-maxrate", res_config["video_bitrate"],
            "-bufsize", "2M",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", res_config["audio_bitrate"],
            "-movflags", "+faststart",
            "-threads", "1",
            output_path
        ]
        
        logger.info(f"Compression {resolution}...")
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Erreur {resolution}: {error_msg}")
            return None
        
        file_size = os.path.getsize(output_path)
        return output_path, file_size
        
    except Exception as e:
        logger.error(f"Erreur compression {resolution}: {e}")
        return None

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les vidéos avec support des gros fichiers"""
    message = update.message
    user_id = message.from_user.id
    
    input_path = None
    temp_files = []
    
    try:
        # Vérifier le type de fichier
        video = message.video or message.document
        if not video:
            await message.reply_text("❌ Envoyez une vidéo valide")
            return

        # Vérifier la taille (maintenant 2GB max)
        if video.file_size > MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ Fichier trop volumineux. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
            return

        start_msg = await message.reply_text("📥 Téléchargement en cours...")
        
        # Télécharger avec le Bot API Server (supporte les gros fichiers)
        file = await context.bot.get_file(video.file_id)
        input_path = os.path.join(OUTPUT_DIR, f"input_{user_id}_{video.file_id}.mp4")
        
        await file.download_to_drive(custom_path=input_path)
        temp_files.append(input_path)
        
        if not os.path.exists(input_path):
            await start_msg.edit_text("❌ Échec téléchargement")
            return

        file_size_mb = os.path.getsize(input_path) // (1024 * 1024)
        await start_msg.edit_text(f"🎬 Compression ({file_size_mb}MB)...")
        
        # Compression séquentielle pour stabilité
        success_count = 0
        for resolution in ["360p", "480p", "720p"]:
            try:
                progress_msg = await message.reply_text(f"🔄 {resolution}...")
                
                result = await compress_video_resolution(input_path, resolution, message, user_id)
                if result:
                    output_path, out_size = result
                    temp_files.append(output_path)
                    
                    out_size_mb = out_size // (1024 * 1024)
                    
                    # Envoyer le fichier (maintenant jusqu'à 2GB via Bot API Server)
                    with open(output_path, 'rb') as f:
                        await message.reply_document(
                            document=f,
                            caption=f"🎬 {resolution} - {out_size_mb}MB"
                        )
                    success_count += 1
                    await progress_msg.edit_text(f"✅ {resolution} - {out_size_mb}MB")
                else:
                    await progress_msg.edit_text(f"❌ {resolution} échouée")
                    
            except Exception as e:
                logger.error(f"Erreur {resolution}: {e}")
                try:
                    await progress_msg.edit_text(f"❌ {resolution} erreur")
                except:
                    pass

        await start_msg.edit_text(f"✅ Terminé! {success_count}/3 versions")

    except Exception as e:
        logger.error(f"Erreur générale: {e}")
        await message.reply_text(f"❌ Erreur: {str(e)[:1000]}")
        
    finally:
        # Nettoyage
        for file_path in temp_files:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Erreur nettoyage: {e}")

def main():
    """Point d'entrée avec Bot API Server"""
    print("🔍 Vérification des dépendances...")
    
    if not check_ffmpeg():
        print("❌ FFmpeg manquant")
        return

    print("🚀 Démarrage avec Bot API Server...")
    print(f"🌐 Bot API Server: {BOT_API_SERVER}")
    print("📹 Fichiers jusqu'à 2GB supportés!")
    
    # Configuration avec Bot API Server
    request = HTTPXRequest(
        base_url=f"{BOT_API_SERVER}/bot",
        connect_timeout=60,
        read_timeout=120,
        write_timeout=120
    )
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .read_timeout(120)
        .write_timeout(120)
        .connect_timeout(60)
        .pool_timeout(120)
        .build()
    )
    
    # Filtres vidéo
    video_filter = (
        filters.VIDEO |
        filters.Document.MP4 |
        filters.Document.MimeType("video/mp4") |
        filters.Document.MimeType("video/quicktime") |
        filters.Document.MimeType("video/x-matroska")
    )
    
    application.add_handler(MessageHandler(video_filter, handle_video))
    
    print("✅ Bot démarré avec Bot API Server!")
    application.run_polling()

if __name__ == "__main__":
    main()
