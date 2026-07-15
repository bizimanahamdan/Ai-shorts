# 🎬 AI Shorts Telegram Bot

A Telegram bot that automatically transforms long-form videos into viral short-form content (TikTok, Instagram Reels, YouTube Shorts). Send a YouTube URL or upload a video, and the bot handles everything — from AI-powered viral moment detection to final 9:16 formatting with captions.

## Features

- **YouTube URL Processing** — Send any YouTube link and get viral shorts back
- **Video File Upload** — Upload videos directly to Telegram for processing
- **AI Viral Moment Detection** — Google Gemini identifies the most engaging segments
- **Automatic Transcription** — OpenAI Whisper generates accurate subtitles
- **Smart Video Cutting** — Extracts 3-6 viral-worthy clips (20-60 seconds each)
- **Caption Overlay** — Burns styled subtitles directly into the video
- **9:16 Vertical Formatting** — Outputs at 1080x1920 for all short-form platforms
- **Metadata Generation** — AI-generated titles, descriptions, and hashtags
- **Thumbnail Creation** — Auto-generated thumbnails for each clip
- **Progress Updates** — Real-time status messages during processing
- **Multi-user Support** — Handles multiple users concurrently

## Architecture

```
User (Telegram) → Bot → Pipeline:
  1. Download Video (yt-dlp)
  2. Extract Audio (FFmpeg)
  3. Transcribe (OpenAI Whisper)
  4. Analyze Viral Moments (Google Gemini)
  5. Cut Shorts (FFmpeg)
  6. Add Captions (FFmpeg + SRT)
  7. Final Processing (9:16, 1080x1920)
  8. Generate Metadata (Google Gemini)
  9. Generate Thumbnails (FFmpeg)
  → Send results back via Telegram
```

## Prerequisites

- Python 3.9+
- FFmpeg installed on your system
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google API Key (for Gemini AI)
- OpenAI API Key (for Whisper transcription)

## Quick Start

### Option 1: Run Directly

```bash
# Clone or download this project
cd AI-Shorts-Bot

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (if not already installed)
# Ubuntu/Debian:
sudo apt install ffmpeg
# macOS:
brew install ffmpeg

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_token_here"
export GOOGLE_API_KEY="your_google_key_here"
export OPENAI_API_KEY="your_openai_key_here"

# Run the bot
python telegram_bot.py
```

### Option 2: Docker

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your API keys

# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option 3: Docker (manual)

```bash
# Build the image
docker build -t ai-shorts-bot .

# Run the container
docker run -d \
  --name ai-shorts-bot \
  -e TELEGRAM_BOT_TOKEN="your_token" \
  -e GOOGLE_API_KEY="your_key" \
  -e OPENAI_API_KEY="your_key" \
  -v $(pwd)/exports:/app/exports \
  -v $(pwd)/logs:/app/logs \
  ai-shorts-bot
```

## Getting API Keys

### 1. Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token provided

### 2. Google API Key (Gemini)

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key

### 3. OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Copy the key

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and instructions |
| `/help` | Detailed help guide with tips |
| `/status` | Check bot status and active jobs |
| `/cancel` | Cancel current video processing |

## Project Structure

```
AI-Shorts-Bot/
├── telegram_bot.py          # Main bot entry point
├── scripts/
│   ├── orchestrator.py      # Pipeline orchestrator
│   ├── download_video.py    # Video download (yt-dlp + local files)
│   ├── extract_audio.py     # Audio extraction (FFmpeg)
│   ├── transcribe_audio.py  # Speech-to-text (Whisper)
│   ├── analyze_viral_moments.py  # AI analysis (Gemini)
│   ├── cut_video.py         # Video cutting (FFmpeg)
│   ├── add_captions_emojis.py    # Caption overlay (FFmpeg)
│   ├── final_video_processing.py # Final formatting
│   ├── generate_metadata.py      # AI metadata (Gemini)
│   └── generate_thumbnail.py     # Thumbnail generation
├── downloads/               # Downloaded videos (temporary)
├── transcripts/             # Audio files and SRT transcripts
├── clips/                   # Cut video segments
├── captions/                # Captioned videos
├── exports/                 # Final processed shorts
├── thumbnails/              # Generated thumbnails
├── logs/                    # Application logs
├── Dockerfile               # Docker build file
├── docker-compose.yml       # Docker Compose config
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
└── README.md                # This file
```

## Configuration

All configuration is done via environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |
| `OPENAI_API_KEY` | Yes | OpenAI API key for Whisper |

## How It Works

1. **User sends a YouTube URL or uploads a video** to the Telegram bot
2. **Video is downloaded** using yt-dlp (or saved from Telegram upload)
3. **Audio is extracted** from the video using FFmpeg
4. **Audio is transcribed** to SRT format using OpenAI Whisper
5. **Google Gemini analyzes** the transcript to find 3-6 viral moments
6. **FFmpeg cuts** the video at the identified timestamps
7. **Captions are burned** into each clip with styled subtitles
8. **Final processing** converts to 9:16 vertical format (1080x1920)
9. **Gemini generates** optimized titles, descriptions, and hashtags
10. **Thumbnails are created** from key frames
11. **Results are sent** back to the user via Telegram with all assets

## Deployment Options

### Hugging Face Spaces (Free)

1. Create a new Space with Docker SDK
2. Upload all project files
3. Set environment variables in Space settings
4. The bot will start automatically

### Railway / Render / Fly.io

1. Connect your GitHub repository
2. Set environment variables in the dashboard
3. Deploy with the included Dockerfile

### VPS (DigitalOcean, Hetzner, etc.)

1. SSH into your server
2. Install Docker and Docker Compose
3. Clone the project and set up `.env`
4. Run `docker-compose up -d`

### Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install python ffmpeg git
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="your_token"
export GOOGLE_API_KEY="your_key"
export OPENAI_API_KEY="your_key"
python telegram_bot.py
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot not responding | Check `TELEGRAM_BOT_TOKEN` is correct |
| Download fails | Update yt-dlp: `pip install --upgrade yt-dlp` |
| Transcription fails | Verify `OPENAI_API_KEY` and account has credits |
| Viral analysis fails | Check `GOOGLE_API_KEY` and Gemini API access |
| FFmpeg errors | Ensure FFmpeg is installed: `ffmpeg -version` |
| Large file errors | Telegram limits uploads to 50MB; use URLs for larger videos |

## Limitations

- Telegram file upload limit: 50MB (use YouTube URLs for larger videos)
- Processing time: 3-10 minutes per video depending on length
- Recommended video length: 3-30 minutes
- One active job per user at a time
- API rate limits apply (Gemini free tier, OpenAI usage-based)

## License

MIT License — feel free to use, modify, and distribute.
