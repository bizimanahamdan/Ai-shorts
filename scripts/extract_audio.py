import subprocess
import os
import logging

logger = logging.getLogger(__name__)


def extract_audio(video_path, output_audio_path="/home/ubuntu/AI-Shorts-Bot/transcripts/"):
    """
    Extracts audio from a video file using FFmpeg.
    Args:
        video_path (str): The path to the input video file.
        output_audio_path (str): The directory where the audio will be saved.
    Returns:
        str: The path to the extracted audio file, or None if extraction fails.
    """
    if not os.path.exists(output_audio_path):
        os.makedirs(output_audio_path)

    video_filename = os.path.basename(video_path)
    audio_filename = os.path.splitext(video_filename)[0] + ".mp3"
    full_output_audio_path = os.path.join(output_audio_path, audio_filename)

    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "192k",
        "-ar", "44100",
        "-y",
        full_output_audio_path
    ]

    try:
        logger.info(f"Extracting audio from: {video_path}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"Audio extraction successful: {full_output_audio_path}")
        return full_output_audio_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during audio extraction: {e}")
        logger.error(e.stderr)
        return None
    except FileNotFoundError:
        logger.error("Error: FFmpeg not found. Please ensure it is installed and in your PATH.")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dummy_video_path = "/home/ubuntu/AI-Shorts-Bot/downloads/test_video.mp4"
    audio_file = extract_audio(dummy_video_path)
    if audio_file:
        print(f"Audio extracted to: {audio_file}")
    else:
        print("Audio extraction failed.")
