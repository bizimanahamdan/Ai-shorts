"""
AI Shorts Telegram Bot
======================
A Telegram bot that transforms long-form videos into viral short videos.
Users can send YouTube URLs or upload video files directly.
"""

import os
import sys
import re
import json
import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

from scripts.orchestrator import orchestrate_video_workflow

# ─── Configuration ───────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BASE_DIR = "/home/ubuntu/AI-Shorts-Bot"
MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram upload limit

# ─── Logging Setup ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(BASE_DIR, "logs", "bot.log")),
    ],
)
logger = logging.getLogger(__name__)

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
    # Handle youtu.be without https
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

    # Check if user already has an active job
    if user_id in active_jobs:
        await update.message.reply_text(
            "⏳ You already have a video being processed. "
            "Please wait for it to finish or use /cancel to stop it."
        )
        return

    # Extract URL
    url = extract_url(message_text)
    if not url:
        await update.message.reply_text(
            "❌ I couldn't find a valid URL in your message. "
            "Please send a YouTube link or upload a video file."
        )
        return

    # Start processing
    await process_video(update, context, url)


async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded video files."""
    user_id = update.effective_user.id

    # Check if user already has an active job
    if user_id in active_jobs:
        await update.message.reply_text(
            "⏳ You already have a video being processed. "
            "Please wait for it to finish or use /cancel to stop it."
        )
        return

    # Get the file
    if update.message.video:
        file = update.message.video
        file_name = file.file_name or f"video_{user_id}_{int(datetime.now().timestamp())}.mp4"
    elif update.message.document:
        file = update.message.document
        file_name = file.file_name or f"document_{user_id}_{int(datetime.now().timestamp())}"
        # Check if it's a video file
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v']
        if not any(file_name.lower().endswith(ext) for ext in video_extensions):
            mime = file.mime_type or ""
            if "video" not in mime:
                await update.message.reply_text(
                    "❌ This doesn't appear to be a video file. "
                    "Please upload a video (MP4, MKV, AVI, MOV, WebM) or send a YouTube URL."
                )
                return
    else:
        await update.message.reply_text(
            "❌ I couldn't process this file. Please upload a video or send a YouTube URL."
        )
        return

    # Download the file from Telegram
    status_msg = await update.message.reply_text("📥 Downloading your video from Telegram...")

    try:
        downloads_dir = os.path.join(BASE_DIR, "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        local_path = os.path.join(downloads_dir, file_name)

        telegram_file = await context.bot.get_file(file.file_id)
        await telegram_file.download_to_drive(local_path)

        await status_msg.edit_text(f"✅ Video downloaded ({file_name}). Starting processing...")
        logger.info(f"User {user_id} uploaded video: {local_path}")

        # Process the local file
        await process_video(update, context, local_path, status_msg=status_msg)

    except Exception as e:
        logger.error(f"Error downloading file from Telegram: {e}")
        await status_msg.edit_text(
            f"❌ Error downloading your video: {str(e)}\n"
            "Please try again or use a YouTube URL instead."
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle general text messages."""
    text = update.message.text

    if is_youtube_url(text) or extract_url(text):
        await handle_url_message(update, context)
    else:
        await update.message.reply_text(
            "🤔 I'm not sure what to do with that. Here's what I can help with:\n\n"
            "• Send me a *YouTube URL* to create shorts\n"
            "• *Upload a video file* directly\n"
            "• Use /help for more information\n",
            parse_mode="Markdown"
        )


# ─── Video Processing ────────────────────────────────────────────────────────

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                        video_input: str, status_msg=None):
    """Process a video through the full pipeline."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Mark job as active
    active_jobs[user_id] = {
        "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cancelled": False,
        "input": video_input,
    }

    # Send initial status
    if not status_msg:
        status_msg = await update.message.reply_text(
            "🚀 *Starting video processing pipeline...*\n\n"
            "This may take 3-10 minutes depending on video length.\n"
            "I'll send you progress updates along the way!",
            parse_mode="Markdown"
        )

    progress_messages = []

    async def send_progress(step, total, message):
        """Send progress update to user."""
        if user_id in active_jobs and active_jobs[user_id].get("cancelled"):
            return
        progress_bar = "▓" * step + "░" * (total - step)
        progress_text = f"[{progress_bar}] {step}/{total}\n{message}"
        try:
            await context.bot.send_message(chat_id=chat_id, text=progress_text)
        except Exception as e:
            logger.warning(f"Failed to send progress: {e}")

    def sync_progress_callback(step, total, message):
        """Synchronous wrapper for async progress callback."""
        progress_messages.append((step, total, message))

    try:
        # Run the orchestrator in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        # Send periodic progress updates
        async def progress_updater():
            last_count = 0
            while user_id in active_jobs and not active_jobs[user_id].get("cancelled"):
                await asyncio.sleep(3)
                if len(progress_messages) > last_count:
                    for msg in progress_messages[last_count:]:
                        await send_progress(*msg)
                    last_count = len(progress_messages)

        # Start progress updater
        progress_task = asyncio.create_task(progress_updater())

        # Run the heavy processing in executor
        result = await loop.run_in_executor(
            executor,
            lambda: orchestrate_video_workflow(video_input, progress_callback=sync_progress_callback)
        )

        # Stop progress updater
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

        # Check if cancelled
        if user_id in active_jobs and active_jobs[user_id].get("cancelled"):
            return

        # Handle result
        if result["status"] == "error":
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ *Processing Failed*\n\n{result['message']}\n\nPlease try again or use a different video.",
                parse_mode="Markdown"
            )
        elif result["status"] == "success":
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ *Processing Complete!*\n\n"
                    f"🎬 Generated *{result['total_shorts']}* short videos.\n"
                    f"Sending them now..."
                ),
                parse_mode="Markdown"
            )

            # Send each short video with its metadata
            for item in result.get("results", []):
                await send_short_result(context, chat_id, item)

            # Final summary
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🎉 *All done!*\n\n"
                    f"Sent {result['total_shorts']} viral shorts ready for posting.\n"
                    f"Send me another video whenever you're ready! 🚀"
                ),
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Error processing video for user {user_id}: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ *Unexpected Error*\n\n{str(e)}\n\nPlease try again.",
            parse_mode="Markdown"
        )

    finally:
        # Remove active job
        if user_id in active_jobs:
            del active_jobs[user_id]


async def send_short_result(context, chat_id, item):
    """Send a single short video result to the user."""
    try:
        video_path = item.get("video_path")
        thumbnail_path = item.get("thumbnail_path")
        metadata = item.get("metadata")
        moment_data = item.get("moment_data", {})
        short_number = item.get("short_number", 0)

        # Build caption
        caption_parts = [f"🎬 *Short #{short_number}*"]

        if metadata:
            if metadata.get("title"):
                caption_parts.append(f"\n📌 *{metadata['title']}*")
            if metadata.get("description"):
                caption_parts.append(f"\n📝 {metadata['description']}")
            if metadata.get("hashtags"):
                caption_parts.append(f"\n🏷️ {metadata['hashtags']}")
        elif moment_data:
            if moment_data.get("title"):
                caption_parts.append(f"\n📌 *{moment_data['title']}*")
            if moment_data.get("reason"):
                caption_parts.append(f"\n📝 {moment_data['reason']}")
            if moment_data.get("hashtags"):
                hashtags = " ".join(moment_data["hashtags"]) if isinstance(moment_data["hashtags"], list) else moment_data["hashtags"]
                caption_parts.append(f"\n🏷️ {hashtags}")

        caption = "\n".join(caption_parts)

        # Send video
        if video_path and os.path.exists(video_path):
            file_size = os.path.getsize(video_path)

            if file_size <= MAX_TELEGRAM_FILE_SIZE:
                with open(video_path, "rb") as video_file:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=video_file,
                        caption=caption[:1024],  # Telegram caption limit
                        parse_mode="Markdown",
                        supports_streaming=True
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"{caption}\n\n"
                        f"⚠️ Video file is too large for Telegram ({file_size // (1024*1024)}MB). "
                        f"File saved locally at: `{video_path}`"
                    ),
                    parse_mode="Markdown"
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{caption}\n\n⚠️ Video file not found.",
                parse_mode="Markdown"
            )

        # Send thumbnail
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, "rb") as thumb_file:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=thumb_file,
                    caption=f"🖼️ Thumbnail for Short #{short_number}"
                )

    except Exception as e:
        logger.error(f"Error sending short result: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Error sending Short #{item.get('short_number', '?')}: {str(e)}"
        )


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        print("ERROR: Please set the TELEGRAM_BOT_TOKEN environment variable.")
        print("Get a token from @BotFather on Telegram.")
        sys.exit(1)

    # Ensure directories exist
    for dir_name in ["downloads", "transcripts", "clips", "captions", "exports", "thumbnails", "logs"]:
        os.makedirs(os.path.join(BASE_DIR, dir_name), exist_ok=True)

    logger.info("Starting AI Shorts Telegram Bot...")

    # Build application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    # Add message handlers
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video_upload))
    application.add_handler(MessageHandler(
        filters.Document.MimeType("video/mp4") |
        filters.Document.MimeType("video/x-matroska") |
        filters.Document.MimeType("video/avi") |
        filters.Document.MimeType("video/quicktime") |
        filters.Document.MimeType("video/webm"),
        handle_video_upload
    ))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Set bot commands
    async def post_init(application):
        await application.bot.set_my_commands([
            BotCommand("start", "Start the bot & show welcome"),
            BotCommand("help", "Show help guide"),
            BotCommand("status", "Check bot & job status"),
            BotCommand("cancel", "Cancel current processing"),
        ])

    application.post_init = post_init

    # Start polling
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
