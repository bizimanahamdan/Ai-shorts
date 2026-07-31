import subprocess
import os
import logging
import shutil
import time
import requests

logger = logging.getLogger(__name__)

def download_video(url_or_path, output_path="/home/ubuntu/AI-Shorts-Bot/downloads/"):
    """
    Downloads a video from a given URL using a Free API, falls back to yt-dlp, or copies a local file.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # 1. Check if it's a local file path (Direct Telegram Upload)
    if os.path.isfile(url_or_path):
        logger.info(f"Local file detected: {url_or_path}")
        filename = os.path.basename(url_or_path)
        dest_path = os.path.join(output_path, filename)
        try:
            shutil.copy2(url_or_path, dest_path)
            logger.info(f"File copied to: {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Error copying local file: {e}")
            return None

    # 2. Try Free Downloader API First (Bypasses Render's YouTube Blocks)
    logger.info(f"Attempting to download via Free API for: {url_or_path}")
    try:
        api_url = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        payload = {
            "url": url_or_path,
            "videoQuality": "1080",
            "isAudioOnly": False
        }
        
        response = requests.post(api_url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            video_url = data.get("url")
            
            if video_url:
                logger.info("API Success! Streaming file to Render storage...")
                filename = f"youtube_api_{int(time.time())}.mp4"
                final_dest = os.path.join(output_path, filename)
                
                with requests.get(video_url, stream=True) as r:
                    r.raise_for_status()
                    with open(final_dest, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                logger.info(f"Video downloaded successfully via API to: {final_dest}")
                return final_dest
        else:
            logger.warning("Free API failed or is busy. Falling back to yt-dlp...")
    except Exception as e:
        logger.error(f"API workflow failed: {e}. Falling back to yt-dlp...")

    # 3. Fallback to yt-dlp (With the correct single-file FIX)
    logger.info("Using yt-dlp fallback...")
    command = [
        "yt-dlp",
        "-f", "best[ext=mp4]",  # <-- THIS FIXES THE RENDER CRASH
        "--output", os.path.join(output_path, "%(title)s.%(ext)s"),
        "--extractor-args", "youtube:player_client=android,web",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "--add-header", "Accept-Language:en-US,en;q=0.5",
        "--no-check-certificate",
        url_or_path
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info("yt-dlp download successful.")
        
        for line in result.stdout.splitlines():
            if "Destination:" in line:
                return line.split("Destination:")[1].strip()
            if "has already been downloaded" in line:
                return line.split("[download]")[1].split("has already been downloaded")[0].strip()
                
        files = [os.path.join(output_path, f) for f in os.listdir(output_path) if f.endswith('.mp4')]
        if files:
            return max(files, key=os.path.getmtime)
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during yt-dlp fallback: {e}")
        logger.error(e.stderr)
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    downloaded_file_path = download_video(video_url)
    if downloaded_file_path:
        print(f"Video downloaded to: {downloaded_file_path}")
    else:
        print("Video download failed.")
        
