import os
import subprocess
import asyncio
import logging
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackContext
from telegram.request import HTTPXRequest

# === CONFIGURATION SÉCURISÉE ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WATERMARK_TEXT = os.getenv("WATERMARK_TEXT", "© HazardCompressBot")
OUTPUT_DIR = "output_videos"
MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2GB

# Vérification des variables critiques
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN non défini! Définissez la variable d'environnement BOT_TOKEN")

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Résolutions optimisées
RESOLUTIONS = {
    "144p": {"scale": "256x144", "crf": "28", "audio_bitrate": "64k", "preset": "ultrafast"},
    "240p": {"scale": "426x240", "crf": "27", "audio_bitrate": "96k", "preset": "ultrafast"},
    "360p": {"scale": "640x360", "crf": "26", "audio_bitrate": "96k", "preset": "superfast"},
    "480p": {"scale": "854x480", "crf": "25", "audio_bitrate": "128k", "preset": "superfast"},
    "720p": {"scale": "1280x720", "crf": "23", "audio_bitrate": "128k", "preset": "fast"},
    "1080p": {"scale": "1920x1080", "crf": "21", "audio_bitrate": "192k", "preset": "fast"}
}

def check_ffmpeg():
    """Vérifie si FFmpeg est installé et accessible"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            check=True, 
            capture_output=True, 
            text=True,
            timeout=10
        )
        logger.info("✅ FFmpeg détecté avec succès")
        logger.info(f"FFmpeg version: {result.stdout.splitlines()[0] if result.stdout else 'Unknown'}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur FFmpeg: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("❌ FFmpeg non trouvé dans le PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout lors de la vérification FFmpeg")
        return False

async def download_file_direct(file_url: str, dest_path: str, chunk_size: int = 1024*1024):
    """Télécharge un fichier Telegram via URL directe en streaming (supporte jusqu'à 2GB)."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0)) as session:
            async with session.get(file_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Échec HTTP {resp.status}")
                
                total = 0
                with open(dest_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        total += len(chunk)
                
                logger.info(f"✅ Téléchargement terminé ({total // (1024*1024)}MB)")
                return True
    except Exception as e:
        logger.error(f"❌ Échec téléchargement direct: {e}")
        return False

async def compress_and_send_single(input_path: str, resolution: str, message, user_id, file_id):
    """Compresse et envoie une seule résolution"""
    res_config = RESOLUTIONS[resolution]
    base_name = os.path.splitext(input_path)[0]
    output_path = f"{base_name}_{resolution}.mp4"
    
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"scale={res_config['scale']}",
            "-c:v", "libx264",
            "-crf", res_config["crf"],
            "-preset", res_config["preset"],
            "-c:a", "aac",
            "-b:a", res_config["audio_bitrate"],
            "-movflags", "+faststart",
            "-threads", "2",
            output_path
        ]
        
        logger.info(f"Compression {resolution} en cours...")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Erreur FFmpeg {resolution}: {error_msg}")
            raise Exception(f"FFmpeg error: {error_msg}")
        
        if not os.path.exists(output_path):
            raise Exception("Fichier de sortie non créé")
        
        file_size = os.path.getsize(output_path)
        file_size_mb = file_size // (1024 * 1024)
        
        if file_size < 50 * 1024 * 1024:
            with open(output_path, 'rb') as f:
                await message.reply_document(
                    document=f,
                    caption=f"🎬 {resolution} - {file_size_mb}MB"
                )
            logger.info(f"✅ {resolution} envoyé ({file_size_mb}MB)")
        else:
            await message.reply_text(f"📁 {resolution} - Trop volumineux ({file_size_mb}MB)")
        
        os.remove(output_path)
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur {resolution}: {str(e)}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'upload et la compression des vidéos"""
    message = update.message
    user_id = message.from_user.id
    
    input_path = None
    compression_tasks = []
    
    try:
        video = message.video or message.document
        
        if not video:
            await message.reply_text("❌ Veuillez envoyer une vidéo (MP4, MKV, AVI, MOV...)")
            return

        if video.file_size > MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ Fichier trop volumineux. Taille maximale: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
            return

        start_msg = await message.reply_text("🚀 Démarrage de la compression multi-résolution...")
        
        file_id = video.file_id
        file = await context.bot.get_file(file_id)
        input_path = os.path.join(OUTPUT_DIR, f"input_{user_id}_{file_id}.mp4")
        
        try:
            await file.download_to_drive(custom_path=input_path)
            logger.info(f"Fichier téléchargé: {input_path}")
        except Exception as download_error:
            logger.warning(f"Téléchargement standard échoué, tentative directe: {download_error}")
            try:
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
                success = await download_file_direct(file_url, input_path)
                if not success:
                    raise Exception("Échec du téléchargement direct")
            except Exception as e:
                await start_msg.edit_text(f"❌ Erreur téléchargement: {str(e)}")
                return

        if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
            await start_msg.edit_text("❌ Échec du téléchargement du fichier")
            return

        file_size_mb = os.path.getsize(input_path) // (1024 * 1024)
        await start_msg.edit_text(f"📥 Fichier téléchargé ({file_size_mb}MB) - Lancement des compressions...")
        
        for resolution in RESOLUTIONS.keys():
            task = asyncio.create_task(
                compress_and_send_single(input_path, resolution, message, user_id, file_id)
            )
            compression_tasks.append(task)
        
        results = await asyncio.gather(*compression_tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        
        if success_count > 0:
            await start_msg.edit_text(f"✅ Toutes les compressions sont terminées ! {success_count}/{len(RESOLUTIONS)} versions générées")
        else:
            await start_msg.edit_text("❌ Aucune version n'a pu être générée")

    except Exception as e:
        logger.error(f"Erreur générale: {str(e)}")
        error_msg = f"❌ Erreur lors du traitement: {str(e)}"
        if len(error_msg) > 4000:
            error_msg = "❌ Erreur lors du traitement (message d'erreur trop long)"
        await message.reply_text(error_msg)
        
    finally:
        if input_path and os.path.exists(input_path):
            try:
                os.remove(input_path)
                logger.info("Fichier d'entrée nettoyé")
            except Exception as e:
                logger.error(f"Erreur nettoyage input: {str(e)}")

async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        if update and update.message:
            await update.message.reply_text(
                "❌ Une erreur s'est produite lors du traitement. Veuillez réessayer."
            )
    except:
        pass

def main():
    print("🔍 Vérification de FFmpeg...")
    
    if not check_ffmpeg():
        print("❌ ERREUR CRITIQUE: FFmpeg n'est pas installé ou n'est pas accessible")
        print("💡 Solution: Assurez-vous que FFmpeg est installé dans le conteneur Docker")
        return

    print("✅ FFmpeg détecté - Démarrage du bot...")
    print("🌐 Mode: LOCAL API (fichiers jusqu'à 2GB supportés)")
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(120)
        .write_timeout(120)
        .pool_timeout(120)
        .connect_timeout(120)
        .get_updates_request(HTTPXRequest(http_version="1.1"))
        .build()
    )
    
    video_filter = (
        filters.VIDEO |
        filters.Document.MimeType("video/mp4") |
        filters.Document.MimeType("video/x-matroska") |
        filters.Document.MimeType("video/quicktime") |
        filters.Document.MimeType("video/x-msvideo") |
        filters.Document.MimeType("video/webm")
    )
    
    application.add_handler(MessageHandler(video_filter, handle_video))
    
    print("🚀 Bot démarré avec succès!")
    print("📹 Envoyez une vidéo pour la compresser")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
