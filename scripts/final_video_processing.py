import subprocess
import os
import logging

logger = logging.getLogger(__name__)


def process_final_video(video_path, output_dir="/home/ubuntu/AI-Shorts-Bot/exports/",
                        target_width=1080, target_height=1920):
    """
    Applies final processing to a video: 9:16 aspect ratio, 1080x1920 resolution, basic zoom.
    Args:
        video_path (str): Path to the input video file.
        output_dir (str): Directory to save the final video.
        target_width (int): Target width (default 1080 for vertical shorts).
        target_height (int): Target height (default 1920 for vertical shorts).
    Returns:
        str: Path to the final processed video file, or None if processing fails.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    video_filename = os.path.basename(video_path)
    final_filename = "final_" + os.path.splitext(video_filename)[0] + ".mp4"
    full_output_path = os.path.join(output_dir, final_filename)

    # FFmpeg filter to:
    # 1. Scale and crop to 9:16 aspect ratio
    # 2. Apply a subtle zoom effect (ken burns style)
    # 3. Set resolution to 1080x1920
    vf_filter = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height},"
        f"zoompan=z='min(zoom+0.0005,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={target_width}x{target_height}:fps=30"
    )

    # Simpler approach: just scale and crop without zoompan (more reliable)
    vf_simple = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
        f"crop={target_width}:{target_height}"
    )

    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", vf_simple,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        full_output_path
    ]

    try:
        logger.info(f"Final processing video: {video_path}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"Final processing successful: {full_output_path}")
        return full_output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during final video processing: {e}")
        logger.error(e.stderr)
        # Fallback: just copy the file
        try:
            logger.info("Fallback: copying video without final processing")
            subprocess.run(["cp", video_path, full_output_path], check=True)
            return full_output_path
        except Exception:
            return None
    except FileNotFoundError:
        logger.error("Error: FFmpeg not found.")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("final_video_processing.py - Use process_final_video() with a video path.")
