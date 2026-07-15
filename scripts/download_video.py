import subprocess
import os
import logging
import shutil

logger = logging.getLogger(__name__)


def download_video(url_or_path, output_path="/home/ubuntu/AI-Shorts-Bot/downloads/"):
    """
    Downloads a video from a given URL using yt-dlp, or copies a local file.
    Args:
        url_or_path (str): The URL of the video to download, or a local file path.
        output_path (str): The directory where the video will be saved.
    Returns:
        str: The path to the downloaded/copied video file, or None if it fails.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Check if it's a local file path
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

    # Otherwise, treat as URL and download with yt-dlp
    command = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", os.path.join(output_path, "%(title)s.%(ext)s"),
        "--extractor-args", "youtube:player_client=android,web",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "--add-header", "Accept-Language:en-US,en;q=0.5",
        "--no-check-certificate",
        url_or_path
    ]

    try:
        logger.info(f"Downloading video from: {url_or_path}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info("Download successful.")
        # Extract the downloaded filename from stdout
        for line in result.stdout.splitlines():
            if "Destination:" in line:
                downloaded_file = line.split("Destination:")[1].strip()
                return downloaded_file
            if "[Merger]" in line and "Merging formats into" in line:
                # Handle merged output
                merged_file = line.split("Merging formats into")[1].strip().strip('"')
                return merged_file
        # Fallback: look for the file that was just created
        for line in result.stdout.splitlines():
            if "has already been downloaded" in line:
                # Extract path from "[download] PATH has already been downloaded"
                path = line.split("[download]")[1].split("has already been downloaded")[0].strip()
                return path
        # Last resort: find most recent mp4 in output_path
        files = [os.path.join(output_path, f) for f in os.listdir(output_path) if f.endswith('.mp4')]
        if files:
            return max(files, key=os.path.getmtime)
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during video download: {e}")
        logger.error(e.stderr)
        return None
    except FileNotFoundError:
        logger.error("Error: yt-dlp not found. Please ensure it is installed and in your PATH.")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    downloaded_file_path = download_video(video_url)
    if downloaded_file_path:
        print(f"Video downloaded to: {downloaded_file_path}")
    else:
        print("Video download failed.")
