import os
import json
import sys
import subprocess
import logging

logger = logging.getLogger(__name__)

# Add the scripts directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import download_video
import extract_audio
import transcribe_audio
import analyze_viral_moments
import cut_video
import add_captions_emojis
import final_video_processing
import generate_metadata
import generate_thumbnail


def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
            capture_output=True, text=True, check=True
        )
        duration = float(result.stdout.strip())
        logger.info(f"Video duration: {duration} seconds")
        return duration
    except Exception as e:
        logger.warning(f"Could not get video duration: {e}. Using default 300s.")
        return 300


def orchestrate_video_workflow(video_url_or_path, progress_callback=None):
    """
    Orchestrates the entire video processing workflow.
    Args:
        video_url_or_path (str): URL of the YouTube video or local path to an uploaded video.
        progress_callback (callable): Optional callback function for progress updates.
            Called with (step_number, total_steps, message).
    Returns:
        dict: A dictionary containing paths to all generated assets, or an error message.
    """
    base_dir = "/home/ubuntu/AI-Shorts-Bot"
    downloads_dir = os.path.join(base_dir, "downloads")
    transcripts_dir = os.path.join(base_dir, "transcripts")
    clips_dir = os.path.join(base_dir, "clips")
    captions_dir = os.path.join(base_dir, "captions")
    exports_dir = os.path.join(base_dir, "exports")
    thumbnails_dir = os.path.join(base_dir, "thumbnails")

    # Ensure all directories exist
    for d in [downloads_dir, transcripts_dir, clips_dir, captions_dir, exports_dir, thumbnails_dir]:
        os.makedirs(d, exist_ok=True)

    total_steps = 9

    def update_progress(step, message):
        logger.info(f"[Step {step}/{total_steps}] {message}")
        if progress_callback:
            try:
                progress_callback(step, total_steps, message)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    update_progress(1, f"Starting workflow for: {video_url_or_path}")

    # 1. Download Video
    update_progress(1, "📥 Downloading video...")
    downloaded_video_path = download_video.download_video(video_url_or_path, output_path=downloads_dir)
    if not downloaded_video_path:
        return {"status": "error", "message": "Video download failed. Please check the URL or file."}
    logger.info(f"Downloaded video: {downloaded_video_path}")

    # Get actual video duration
    video_duration_seconds = get_video_duration(downloaded_video_path)

    # 2. Extract Audio
    update_progress(2, "🎵 Extracting audio...")
    audio_path = extract_audio.extract_audio(downloaded_video_path, output_audio_path=transcripts_dir)
    if not audio_path:
        return {"status": "error", "message": "Audio extraction failed."}
    logger.info(f"Extracted audio: {audio_path}")

    # 3. Transcribe Audio
    update_progress(3, "📝 Transcribing audio with Whisper AI...")
    srt_path = transcribe_audio.transcribe_audio(audio_path, output_transcript_path=transcripts_dir)
    if not srt_path:
        return {"status": "error", "message": "Audio transcription failed."}
    logger.info(f"Generated transcript: {srt_path}")

    # 4. Analyze for Viral Moments
    update_progress(4, "🔍 Analyzing for viral moments with Gemini AI...")
    viral_moments_json_path = analyze_viral_moments.analyze_viral_moments(
        srt_path, video_duration_seconds, output_analysis_path=clips_dir
    )
    if not viral_moments_json_path:
        return {"status": "error", "message": "Viral moments analysis failed."}
    logger.info(f"Analyzed viral moments: {viral_moments_json_path}")

    # 5. Cut Video into Shorts
    update_progress(5, "✂️ Cutting video into shorts...")
    cut_video_paths = cut_video.cut_multiple_shorts(downloaded_video_path, viral_moments_json_path, output_dir=clips_dir)
    if not cut_video_paths:
        return {"status": "error", "message": "Video cutting failed or no shorts identified."}
    logger.info(f"Cut {len(cut_video_paths)} short videos")

    # Load viral moments data for metadata and timing
    try:
        with open(viral_moments_json_path, "r") as f:
            all_viral_moments = json.load(f)
    except Exception as e:
        logger.error(f"Error loading viral moments: {e}")
        all_viral_moments = []

    final_results = []

    for i, short_video_path in enumerate(cut_video_paths):
        update_progress(6, f"🎬 Processing short {i+1}/{len(cut_video_paths)}...")

        # Get timing info for this segment
        moment_data = all_viral_moments[i] if i < len(all_viral_moments) else None
        start_seconds = moment_data.get("start_time_seconds", 0) if moment_data else None
        end_seconds = moment_data.get("end_time_seconds", 0) if moment_data else None

        # 6. Add Animated Captions & Emojis
        captioned_video_path = add_captions_emojis.add_captions_and_emojis(
            short_video_path, srt_path, output_video_path=captions_dir,
            start_seconds=start_seconds, end_seconds=end_seconds
        )
        if not captioned_video_path:
            logger.warning(f"Captioning failed for short {i+1}. Using uncaptioned version.")
            captioned_video_path = short_video_path

        # 7. Final Video Processing (Aspect Ratio, Resolution)
        update_progress(7, f"📐 Final processing short {i+1}/{len(cut_video_paths)}...")
        final_processed_video_path = final_video_processing.process_final_video(
            captioned_video_path, output_dir=exports_dir
        )
        if not final_processed_video_path:
            logger.warning(f"Final processing failed for short {i+1}. Using captioned version.")
            final_processed_video_path = captioned_video_path

        # 8. Generate Metadata
        update_progress(8, f"📋 Generating metadata for short {i+1}/{len(cut_video_paths)}...")
        metadata_path = None
        metadata_content = None
        if moment_data:
            try:
                temp_moment_json_path = os.path.join(clips_dir, f"temp_moment_{i}.json")
                with open(temp_moment_json_path, "w") as f_temp:
                    json.dump([moment_data], f_temp, indent=4)

                metadata_path = generate_metadata.generate_metadata(
                    temp_moment_json_path, output_metadata_path=exports_dir
                )

                if metadata_path and os.path.exists(metadata_path):
                    with open(metadata_path, "r") as f:
                        metadata_content = json.loads(f.read())

                # Clean up temp file
                if os.path.exists(temp_moment_json_path):
                    os.remove(temp_moment_json_path)
            except Exception as e:
                logger.error(f"Error generating metadata for short {i+1}: {e}")

        # 9. Generate Thumbnail
        update_progress(9, f"🖼️ Generating thumbnail for short {i+1}/{len(cut_video_paths)}...")
        thumbnail_path = generate_thumbnail.generate_thumbnail(
            final_processed_video_path, output_dir=thumbnails_dir
        )

        result_entry = {
            "short_number": i + 1,
            "video_path": final_processed_video_path,
            "thumbnail_path": thumbnail_path,
            "metadata_path": metadata_path,
            "metadata": metadata_content,
            "moment_data": moment_data
        }
        final_results.append(result_entry)

    return {
        "status": "success",
        "total_shorts": len(final_results),
        "results": final_results,
        "message": f"Workflow completed! Generated {len(final_results)} short videos."
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if len(sys.argv) > 1:
        video_input = sys.argv[1]
    else:
        video_input = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    result = orchestrate_video_workflow(video_input)
    print(json.dumps(result, indent=4))
