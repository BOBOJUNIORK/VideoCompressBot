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
BOT_API_SERVER = os.getenv("BOT_API_SERVER", "http://localhost:8081")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "2000000000"))  # 2GB

# Vérifications critiques
if not all([BOT_TOKEN, API_ID, API_HASH]):
    missing = []
    if not BOT_TOKEN: missing.append("BOT_TOKEN")
    if not API_ID: missing.append("API_ID") 
    if not API_HASH: missing.append("API_HASH")
    raise ValueError(f"❌ Variables manquantes: {', '.join(missing)}")

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dossiers de travail
OUTPUT_DIR = "/tmp/output_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Résolutions optimisées
RESOLUTIONS = {
    "360p": {"scale": "640x360", "crf": "26", "video_bitrate": "800k", "audio_bitrate": "96k", "preset": "fast"},
    "480p": {"scale": "854x480", "crf": "25", "video_bitrate": "1200k", "audio_bitrate": "128k", "preset": "fast"},
    "720p": {"scale": "1280x720", "crf": "23", "video_bitrate": "2500k", "audio_bitrate": "128k", "preset": "medium"},
    "1080p": {"scale": "1920x1080", "crf": "21", "video_bitrate": "5000k", "audio_bitrate": "192k", "preset": "medium"}
}

def check_ffmpeg():
    """Vérifie si FFmpeg est installé"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            logger.info(f"✅ FFmpeg détecté: {version_line}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ FFmpeg non accessible: {e}")
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
            "-preset", res_config["preset"],
            "-c:a", "aac",
            "-b:a", res_config["audio_bitrate"],
            "-movflags", "+faststart",
            "-threads", "2",
            output_path
        ]
        
        logger.info(f"Compression {resolution} en cours...")
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Erreur FFmpeg {resolution}: {error_msg}")
            return None
        
        if not os.path.exists(output_path):
            raise Exception("Fichier de sortie non créé")
            
        file_size = os.path.getsize(output_path)
        return output_path, file_size
        
    except Exception as e:
        logger.error(f"Erreur compression {resolution}: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'upload et la compression des vidéos"""
    message = update.message
    user_id = message.from_user.id
    
    input_path = None
    temp_files = []
    
    try:
        # Vérifier le type de fichier
        video = message.video or message.document
        if not video:
            await message.reply_text("❌ Veuillez envoyer une vidéo (MP4, MKV, AVI, MOV...)")
            return

        # Vérifier la taille
        if video.file_size > MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ Fichier trop volumineux ({video.file_size//(1024*1024)}MB). "
                f"Maximum: {MAX_FILE_SIZE//(1024*1024)}MB"
            )
            return

        start_msg = await message.reply_text("📥 Téléchargement de la vidéo...")
        
        # Télécharger avec le Bot API Server
        file = await context.bot.get_file(video.file_id)
        input_path = os.path.join(OUTPUT_DIR, f"input_{user_id}_{video.file_id}.mp4")
        
        await file.download_to_drive(custom_path=input_path)
        temp_files.append(input_path)
        
        if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
            await start_msg.edit_text("❌ Échec du téléchargement")
            return

        file_size_mb = os.path.getsize(input_path) // (1024 * 1024)
        await start_msg.edit_text(f"🎬 Compression en cours... ({file_size_mb}MB)")
        
        # Compression séquentielle pour stabilité
        success_count = 0
        for resolution in ["360p", "480p", "720p"]:
            try:
                progress_msg = await message.reply_text(f"🔄 Compression {resolution}...")
                
                result = await compress_video_resolution(input_path, resolution, message, user_id)
                if result:
                    output_path, out_size = result
                    temp_files.append(output_path)
                    
                    out_size_mb = out_size // (1024 * 1024)
                    
                    # Envoyer le fichier (support jusqu'à 2GB via Bot API Server)
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
                    await progress_msg.edit_text(f"❌ Erreur {resolution}")
                except:
                    pass

        await start_msg.edit_text(f"✅ Toutes les compressions sont terminées ! {success_count}/3 versions générées")

    except Exception as e:
        logger.error(f"Erreur générale: {e}")
        error_msg = f"❌ Erreur lors du traitement: {str(e)}"
        if len(error_msg) > 1000:
            error_msg = "❌ Erreur lors du traitement"
        await message.reply_text(error_msg)
        
    finally:
        # Nettoyage agressif
        for file_path in temp_files:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Erreur nettoyage {file_path}: {e}")

def main():
    """Point d'entrée principal"""
    print("🔍 Vérification des dépendances...")
    
    if not check_ffmpeg():
        print("❌ ERREUR: FFmpeg n'est pas installé ou accessible")
        return

    print("🚀 Démarrage avec Bot API Server...")
    print(f"🌐 Bot API Server: {BOT_API_SERVER}")
    print(f"📹 Taille max fichier: {MAX_FILE_SIZE//(1024*1024)}MB")
    print("✅ Prêt à recevoir des vidéos!")
    
    # Configuration avec Bot API Server
    request = HTTPXRequest(
        base_url=f"{BOT_API_SERVER}/bot",
        connect_timeout=60,
        read_timeout=120,
        write_timeout=120,
        http_version="1.1"
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
    
    # Filtres pour les types de vidéos supportés
    video_filter = (
        filters.VIDEO |
        filters.Document.MP4 |
        filters.Document.MimeType("video/mp4") |
        filters.Document.MimeType("video/x-matroska") |
        filters.Document.MimeType("video/quicktime") |
        filters.Document.MimeType("video/x-msvideo")
    )
    
    application.add_handler(MessageHandler(video_filter, handle_video))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
