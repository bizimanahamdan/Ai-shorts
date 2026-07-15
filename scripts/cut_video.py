import subprocess
import os
import json
import logging

logger = logging.getLogger(__name__)


def cut_short(video_path, start_time_seconds, end_time_seconds, output_path):
    """
    Cuts a segment from a video using FFmpeg.
    Args:
        video_path (str): Path to the input video file.
        start_time_seconds (float): Start time of the segment in seconds.
        end_time_seconds (float): End time of the segment in seconds.
        output_path (str): Full path for the output video file.
    Returns:
        str: Path to the cut video file, or None if cutting fails.
    """
    duration = end_time_seconds - start_time_seconds
    command = [
        "ffmpeg",
        "-ss", str(start_time_seconds),
        "-i", video_path,
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-strict", "experimental",
        "-y",
        output_path
    ]

    try:
        logger.info(f"Cutting video: {start_time_seconds}s to {end_time_seconds}s -> {output_path}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"Video cut successful: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during video cutting: {e}")
        logger.error(e.stderr)
        return None
    except FileNotFoundError:
        logger.error("Error: FFmpeg not found.")
        return None


def cut_multiple_shorts(video_path, viral_moments_json_path, output_dir="/home/ubuntu/AI-Shorts-Bot/clips/"):
    """
    Cuts multiple short videos based on viral moments analysis.
    Args:
        video_path (str): Path to the input video file.
        viral_moments_json_path (str): Path to the JSON file with viral moments.
        output_dir (str): Directory to save the cut videos.
    Returns:
        list: List of paths to cut video files, or empty list if cutting fails.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(viral_moments_json_path, "r") as f:
            viral_moments = json.load(f)
    except Exception as e:
        logger.error(f"Error reading viral moments JSON: {e}")
        return []

    cut_paths = []
    video_basename = os.path.splitext(os.path.basename(video_path))[0]

    for i, moment in enumerate(viral_moments):
        start_time = moment.get("start_time_seconds", 0)
        end_time = moment.get("end_time_seconds", 0)
        title = moment.get("title", f"short_{i+1}")

        # Sanitize title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]

        output_filename = f"{video_basename}_short_{i+1}_{safe_title}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        result = cut_short(video_path, start_time, end_time, output_path)
        if result:
            cut_paths.append(result)
        else:
            logger.warning(f"Failed to cut short {i+1}: {title}")

    logger.info(f"Cut {len(cut_paths)} shorts from {video_path}")
    return cut_paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("cut_video.py - Use cut_multiple_shorts() with a video path and viral moments JSON.")
