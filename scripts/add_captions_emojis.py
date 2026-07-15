import subprocess
import os
import re
import logging

logger = logging.getLogger(__name__)


def parse_srt_time(time_str):
    """Convert SRT time format (HH:MM:SS,mmm) to seconds."""
    match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_str.strip())
    if match:
        h, m, s, ms = match.groups()
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    return 0.0


def seconds_to_srt_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def filter_srt_for_segment(srt_path, start_seconds, end_seconds, output_srt_path):
    """
    Filter and re-time SRT entries for a specific video segment.
    Args:
        srt_path (str): Path to the original full SRT file.
        start_seconds (float): Start time of the segment.
        end_seconds (float): End time of the segment.
        output_srt_path (str): Path to save the filtered SRT.
    Returns:
        str: Path to the filtered SRT file, or None if it fails.
    """
    try:
        with open(srt_path, 'r') as f:
            content = f.read()

        # Parse SRT entries
        entries = re.split(r'\n\n+', content.strip())
        filtered_entries = []
        counter = 1

        for entry in entries:
            lines = entry.strip().split('\n')
            if len(lines) >= 3:
                # Parse timing line
                time_match = re.match(r'(.+?)\s*-->\s*(.+)', lines[1])
                if time_match:
                    entry_start = parse_srt_time(time_match.group(1))
                    entry_end = parse_srt_time(time_match.group(2))

                    # Check if this entry overlaps with our segment
                    if entry_end > start_seconds and entry_start < end_seconds:
                        # Re-time relative to segment start
                        new_start = max(0, entry_start - start_seconds)
                        new_end = min(end_seconds - start_seconds, entry_end - start_seconds)

                        new_time_line = f"{seconds_to_srt_time(new_start)} --> {seconds_to_srt_time(new_end)}"
                        text = '\n'.join(lines[2:])

                        filtered_entries.append(f"{counter}\n{new_time_line}\n{text}")
                        counter += 1

        if filtered_entries:
            with open(output_srt_path, 'w') as f:
                f.write('\n\n'.join(filtered_entries) + '\n')
            return output_srt_path
        else:
            logger.warning(f"No SRT entries found for segment {start_seconds}s-{end_seconds}s")
            return None

    except Exception as e:
        logger.error(f"Error filtering SRT: {e}")
        return None


def add_captions_and_emojis(video_path, srt_path, output_video_path="/home/ubuntu/AI-Shorts-Bot/captions/",
                            start_seconds=None, end_seconds=None):
    """
    Adds captions to a video using FFmpeg with SRT subtitles burned in.
    Args:
        video_path (str): Path to the input video file.
        srt_path (str): Path to the SRT subtitle file.
        output_video_path (str): Directory to save the captioned video.
        start_seconds (float): Start time of this segment in the original video (for SRT filtering).
        end_seconds (float): End time of this segment in the original video (for SRT filtering).
    Returns:
        str: Path to the captioned video file, or None if it fails.
    """
    if not os.path.exists(output_video_path):
        os.makedirs(output_video_path)

    video_filename = os.path.basename(video_path)
    captioned_filename = os.path.splitext(video_filename)[0] + "_captioned.mp4"
    full_output_path = os.path.join(output_video_path, captioned_filename)

    # If start/end times provided, filter the SRT for this segment
    actual_srt_path = srt_path
    if start_seconds is not None and end_seconds is not None:
        filtered_srt_path = os.path.join(output_video_path, 
                                          os.path.splitext(video_filename)[0] + "_segment.srt")
        filtered = filter_srt_for_segment(srt_path, start_seconds, end_seconds, filtered_srt_path)
        if filtered:
            actual_srt_path = filtered
        else:
            logger.warning("SRT filtering returned no entries, using original SRT")

    # Escape special characters in path for FFmpeg filter
    escaped_srt_path = actual_srt_path.replace("'", "'\\''").replace(":", "\\:")

    # FFmpeg command to burn subtitles with styling
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"subtitles='{escaped_srt_path}':force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=30'",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-y",
        full_output_path
    ]

    try:
        logger.info(f"Adding captions to: {video_path}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"Captions added successfully: {full_output_path}")
        return full_output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error adding captions: {e}")
        logger.error(e.stderr)
        # Fallback: try without subtitles (just copy)
        try:
            logger.info("Fallback: copying video without captions")
            subprocess.run(["cp", video_path, full_output_path], check=True)
            return full_output_path
        except Exception:
            return None
    except FileNotFoundError:
        logger.error("Error: FFmpeg not found.")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("add_captions_emojis.py - Use add_captions_and_emojis() with video and SRT paths.")
