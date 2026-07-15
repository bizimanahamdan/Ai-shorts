import subprocess
import os
import logging

logger = logging.getLogger(__name__)


def generate_thumbnail(video_path, output_dir="/home/ubuntu/AI-Shorts-Bot/thumbnails/", time_in_seconds=5):
    """
    Generates a thumbnail from a video file at a specific time.
    Args:
        video_path (str): Path to the input video file.
        output_dir (str): Directory to save the thumbnail.
        time_in_seconds (int): Time in seconds from which to capture the thumbnail.
    Returns:
        str: Path to the generated thumbnail image file, or None if generation fails.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    video_filename = os.path.basename(video_path)
    thumbnail_filename = os.path.splitext(video_filename)[0] + "_thumbnail.jpg"
    full_output_path = os.path.join(output_dir, thumbnail_filename)

    command = [
        "ffmpeg",
        "-ss", str(time_in_seconds),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        "-y",
        full_output_path
    ]

    try:
        logger.info(f"Generating thumbnail from {video_path} at {time_in_seconds} seconds.")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"Thumbnail generated: {full_output_path}")
        return full_output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during thumbnail generation: {e}")
        logger.error(e.stderr)
        # Try at time 0 as fallback
        try:
            command[2] = "0"
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            logger.info(f"Thumbnail generated (fallback at 0s): {full_output_path}")
            return full_output_path
        except Exception:
            return None
    except FileNotFoundError:
        logger.error("Error: FFmpeg not found.")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("generate_thumbnail.py - Use generate_thumbnail() with a video path.")
