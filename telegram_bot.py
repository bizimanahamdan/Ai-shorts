import os
import sys
import re
import asyncio
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─── Dynamic Paths & Directories ─────────────────────────────────────────────
# Get the directory where your script is actually running
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Automatically create all required directories dynamically
for dir_name in ["downloads", "transcripts", "clips", "captions", "exports", "thumbnails", "logs"]:
    os.makedirs(os.path.join(BASE_DIR, dir_name), exist_ok=True)

# Add scripts directory to path relative to BASE_DIR
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from scripts.orchestrator import orchestrate_video_workflow

# ─── Consolidated Logging Setup ───────────────────────────────────────────────
LOG_FILE = os.path.join(BASE_DIR, "logs", "bot.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE),
    ],
)
logger = logging.getLogger(__name__)

# ─── Non-Blocking Dummy Web Server for Render ─────────────────────────────────
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    # Allow port reuse to avoid address-already-in-use errors
    TCPServer.allow_reuse_address = True
    with TCPServer(("0.0.0.0", port), SimpleHTTPRequestHandler) as httpd:
        logger.info(f"Dummy server running on port {port}")
        httpd.serve_forever()

# Start the dummy server in a separate thread BEFORE doing anything else
threading.Thread(target=run_dummy_server, daemon=True).start()

# ─── Configuration ───────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram upload limit

# Thread pool for running CPU-intensive video processing
executor = ThreadPoolExecutor(max_workers=2)

# Track active jobs per user
active_jobs = {}

# ─── Helper Functions ────────────────────────────────────────────────────────
def is_youtube_url(text):
    """Check if text contains a YouTube URL."""
    youtube_patterns = [
        r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+',
        r'(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(https?://)?youtu\.be/[\w-]+',
    ]
    for pattern in youtube_patterns:
        if re.search(pattern, text):
            return True
    return False

def extract_url(text):
    """Extract URL from message text."""
    url_pattern = r'https?://[^\s<>\"\']+|www\.[^\s<>\"\']+' 
    match = re.search(url_pattern, text)
    if match:
        return match.group(0)
    short_pattern = r'youtu\.be/[\w-]+'
    match = re.search(short_pattern, text)
    if match:
        return "https://" + match.group(0)
    return None

# ─── Command Handlers ────────────────────────────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome_message = (
        "🎬 *AI Shorts Bot* — Transform long videos into viral shorts!\n\n"
        "I can take any YouTube video and automatically:\n"
        "• 📥 Download the video\n"
        "• 📝 Transcribe the audio\n"
        "• 🔍 Find the most viral moments using AI\n"
        "• ✂️ Cut them into short clips\n"
        "• 📐 Format to 9:16 (TikTok/Reels/Shorts)\n"
        "• 🎨 Add captions & generate metadata\n\n"
        "*How to use:*\n"
        "1️⃣ Send me a YouTube URL\n"
        "2️⃣ Or upload a video file directly\n"
        "3️⃣ Wait for the magic to happen! ✨\n\n"
        "*Commands:*\n"
        "/start — Show this welcome message\n"
        "/help — Detailed help & tips\n"
        "/status — Check bot status\n"
        "/cancel — Cancel current processing\n\n"
        "Just send me a video link to get started! 🚀"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_message = (
        "📖 *AI Shorts Bot — Help Guide*\n\n"
        "*Supported Inputs:*\n"
        "• YouTube URLs (full or short links)\n"
        "• Uploaded video files (MP4, MKV, AVI, MOV, WebM)\n\n"
        "*Processing Pipeline:*\n"
        "1. Video download/ingestion\n"
        "2. Audio extraction (FFmpeg)\n"
        "3. Speech-to-text transcription (Whisper AI)\n"
        "4. Viral moment detection (Gemini AI)\n"
        "5. Video cutting into 20-60s segments\n"
        "6. Caption overlay with styling\n"
        "7. 9:16 vertical formatting (1080x1920)\n"
        "8. Metadata generation (titles, hashtags)\n"
        "9. Thumbnail creation\n\n"
        "*Tips:*\n"
        "• Videos between 3-30 minutes work best\n"
        "• Processing takes 3-10 minutes depending on length\n"
        "• You'll get 3-6 short clips per video\n"
        "• Each clip includes metadata for posting\n\n"
        "*Limits:*\n"
        "• Max upload file size: 50MB via Telegram\n"
        "• For larger files, use a YouTube URL instead\n"
        "• One video processed at a time per user\n\n"
        "*Need help?* Just send a message!"
    )
    await update.message.reply_text(help_message, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user_id = update.effective_user.id
    if user_id in active_jobs:
        status_msg = (
            "⚙️ *Bot Status: Running*\n\n"
            f"🔄 You have an active job in progress.\n"
            f"Started: {active_jobs[user_id].get('started', 'Unknown')}\n\n"
            "Use /cancel to stop the current job."
        )
    else:
        status_msg = (
            "✅ *Bot Status: Ready*\n\n"
            "🟢 The bot is online and ready to process videos.\n"
            "📊 No active jobs for your account.\n\n"
            "Send me a YouTube URL or upload a video to start!"
        )
    await update.message.reply_text(status_msg, parse_mode="Markdown")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command."""
    user_id = update.effective_user.id
    if user_id in active_jobs:
        active_jobs[user_id]["cancelled"] = True
        del active_jobs[user_id]
        await update.message.reply_text(
            "🛑 Processing cancelled. You can send a new video whenever you're ready."
        )
    else:
        await update.message.reply_text(
            "ℹ️ No active processing to cancel. Send me a video to get started!"
        )

# ─── Message Handlers ────────────────────────────────────────────────────────
async def handle_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages containing URLs."""
    user_id = update.effective_user.id
    message_text = update.message.text

    if user_id in active_jobs:
        await update.message.reply_text(
            "⏳ You already have a video being processed. Please wait for it to finish."
        )
        return

    url = extract_url(message_text)
    if not url:
        await update.message.reply_text(
            "❌ I couldn't find a valid URL. Please send a YouTube link."
        )
        return

    await process_video(update, context, url)

async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded video files."""
    user_id = update.effective_user.id

    if user_id in active_jobs:
        await update.message.reply_text(
            "⏳ You already have a video being processed. Please wait."
        )
        return

    if update.message.video:
        file = update.message.video
        file_name = file.file_name or f"video_{user_id}_{int(datetime.now().timestamp())}.mp4"
    elif update.message.document:
        file = update.message.document
        file_name = file.file_name or f"document_{user_id}_{int(datetime.now().timestamp())}"
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v']
        if not any(file_name.lower().endswith(ext) for ext in video_extensions):
            mime = file.mime_type or ""
            if "video" not in mime:
                await update.message.reply_text(
                    "❌ This doesn't appear to be a video file. Please upload a valid video format."
                )
                return
    else:
        await update.message.reply_text("❌ Please upload a video file.")
        return

    status_msg = await update.message.reply_text("📥 Downloading video from Telegram...")
    try:
        downloads_dir = os.path.join(BASE_DIR, "downloads")
        local_path = os.path.join(downloads_dir, file_name)
        telegram_file = await context.bot.get_file(file.file_id)
        await telegram_file.download_to_drive(local_path)
        await status_msg.edit_text("✅ Video downloaded. Starting processing...")
        await process_video(update, context, local_path, status_msg=status_msg)
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        await status_msg.edit_text(f"❌ Error downloading: {str(e)}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle general text messages."""
    text = update.message.text
    if is_youtube_url(text) or extract_url(text):
        await handle_url_message(update, context)
    else:
        await update.message.reply_text(
            "🤔 I'm not sure what to do with that. Try sending me a *YouTube URL* or a video file!",
            parse_mode="Markdown"
        )

# ─── Video Processing Pipeline ────────────────────────────────────────────────
async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE, video_input: str, status_msg=None):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    active_jobs[user_id] = {
        "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cancelled": False,
        "input": video_input,
    }

    if not status_msg:
        status_msg = await update.message.reply_text(
            "🚀 *Starting video processing pipeline...*\nThis may take 3-10 minutes.",
            parse_mode="Markdown"
        )

    progress_messages = []

    async def send_progress(step, total, message):
        if user_id in active_jobs and active_jobs[user_id].get("cancelled"):
            return
        progress_bar = "▓" * step + "░" * (total - step)
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"[{progress_bar}] {step}/{total}\n{message}")
        except Exception as e:
            logger.warning(f"Failed to send progress: {e}")

    def sync_progress_callback(step, total, message):
        progress_messages.append((step, total, message))

    try:
        loop = asyncio.get_event_loop()

        async def progress_updater():
            last_count = 0
            while user_id in active_jobs and not active_jobs[user_id].get("cancelled"):
                await asyncio.sleep(3)
                if len(progress_messages) > last_count:
                    for msg in progress_messages[last_count:]:
                        await send_progress(*msg)
                    last_count = len(progress_messages)

        progress_task = asyncio.create_task(progress_updater())

        result = await loop.run_in_executor(
            executor,
            lambda: orchestrate_video_workflow(video_input, progress_callback=sync_progress_callback)
        )

        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

        if user_id in active_jobs and active_jobs[user_id].get("cancelled"):
            return

        if result["status"] == "error":
            await context.bot.send_message(chat_id=chat_id, text=f"❌ *Processing Failed*\n\n{result['message']}", parse_mode="Markdown")
        elif result["status"] == "success":
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ *Processing Complete!*\nGenerated *{result['total_shorts']}* shorts. Sending...",
                parse_mode="Markdown"
            )

            for item in result.get("results", []):
                await send_short_result(context, chat_id, item)

            await context.bot.send_message(chat_id=chat_id, text="🎉 *All done!* Ready for the next video.", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text=f"❌ *Unexpected Error*\n\n{str(e)}")
    finally:
        if user_id in active_jobs:
            del active_jobs[user_id]

async def send_short_result(context, chat_id, item):
    try:
        video_path = item.get("video_path")
        thumbnail_path = item.get("thumbnail_path")
        metadata = item.get("metadata")
        moment_data = item.get("moment_data", {})
        short_number = item.get("short_number", 0)

        caption_parts = [f"🎬 *Short #{short_number}*"]
        if metadata:
            if metadata.get("title"): caption_parts.append(f"\n📌 *{metadata['title']}*")
            if metadata.get("description"): caption_parts.append(f"\n📝 {metadata['description']}")
            if metadata.get("hashtags"): caption_parts.append(f"\n🏷️ {metadata['hashtags']}")
        elif moment_data:
            if moment_data.get("title"): caption_parts.append(f"\n📌 *{moment_data['title']}*")
            if moment_data.get("reason"): caption_parts.append(f"\n📝 {moment_data['reason']}")
            if moment_data.get("hashtags"):
                hashtags = " ".join(moment_data["hashtags"]) if isinstance(moment_data["hashtags"], list) else moment_data["hashtags"]
                caption_parts.append(f"\n🏷️ {hashtags}")

        caption = "\n".join(caption_parts)

        if video_path and os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            if file_size <= MAX_TELEGRAM_FILE_SIZE:
                with open(video_path, "rb") as video_file:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=video_file,
                        caption=caption[:1024],
                        parse_mode="Markdown",
                        supports_streaming=True
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{caption}\n\n⚠️ Video too large for Telegram ({file_size // (1024*1024)}MB). Saved at: `{video_path}`",
                    parse_mode="Markdown"
                )
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"{caption}\n\n⚠️ Video file not found.")

        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, "rb") as thumb_file:
                await context.bot.send_photo(chat_id=chat_id, photo=thumb_file, caption=f"🖼️ Thumbnail for Short #{short_number}")
    except Exception as e:
        logger.error(f"Error sending short: {e}")

# ─── Main Execution ──────────────────────────────────────────────────────────
import asyncio
import sys

# ... your other code ...

async def main_async():
    """Asynchronous main function to properly handle Python 3.14 event loops"""
    # 1. Initialize your application (replace this with your actual build step)
    # application = Application.builder().token(YOUR_TOKEN).build()
    
    # 2. Run the polling bot inside the active loop
    # run_polling is normally synchronous but can be run within an existing loop.
    # To prevent event loop conflicts, we run it using the application's native async cycle:
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot is running in async mode! Press Ctrl+C to stop.")
        
        # Keep the bot running until interrupted
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

def main():
    logger.info("Starting AI Shorts Telegram Bot...")
    
    # Start your dummy server thread/process here (if you are using one)
    # start_dummy_server() 

    # Explicitly run our async loop on Python 3.14+
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
            
