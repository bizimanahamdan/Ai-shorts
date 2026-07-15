import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


def format_time(seconds):
    """
    Converts seconds (float) into SRT time format: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds % 1) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def json_to_srt(segments):
    """
    Converts Whisper verbose_json segments list into an SRT string format.
    """
    srt_content = []
    for index, segment in enumerate(segments, start=1):
        start = format_time(segment['start'])
        end = format_time(segment['end'])
        text = segment['text'].strip()
        
        srt_content.append(f"{index}")
        srt_content.append(f"{start} --> {end}")
        srt_content.append(text)
        srt_content.append("")  # Empty line between subtitle blocks
        
    return "\n".join(srt_content)


def transcribe_audio(audio_path, output_transcript_path="/home/ubuntu/AI-Shorts-Bot/transcripts/"):
    """
    Transcribes an audio file using Groq's FREE Whisper API.
    Args:
        audio_path (str): The path to the input audio file.
        output_transcript_path (str): The directory where the transcript will be saved.
    Returns:
        str: The path to the generated transcript file (SRT format), or None if transcription fails.
    """
    # Adjust output directory for Render's environment dynamically if needed
    if not os.path.exists(output_transcript_path):
        os.makedirs(output_transcript_path)

    audio_filename = os.path.basename(audio_path)
    transcript_filename = os.path.splitext(audio_filename)[0] + ".srt"
    full_output_transcript_path = os.path.join(output_transcript_path, transcript_filename)

    try:
        # 1. Point the OpenAI client to Groq's servers using your free Groq key
        client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

        with open(audio_path, "rb") as audio_file:
            logger.info(f"Transcribing audio file via Groq: {audio_path}")
            
            # 2. Call Groq's Whisper Large V3 Model
            response = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                response_format="verbose_json"  # Required to get segment timestamps
            )

        # 3. Access response dictionary (or object attributes)
        # Convert response object to dict if it's not already one
        response_data = response if isinstance(response, dict) else response.model_dump()
        segments = response_data.get("segments", [])

        if not segments:
            logger.warning("No speech segments found in the transcription.")
            return None

        # 4. Generate the SRT content from the timestamps
        srt_text = json_to_srt(segments)

        # 5. Write the SRT file to disk
        with open(full_output_transcript_path, "w", encoding="utf-8") as f:
            f.write(srt_text)

        logger.info(f"Transcription successful. Saved to: {full_output_transcript_path}")
        return full_output_transcript_path

    except Exception as e:
        logger.error(f"Error during Groq audio transcription: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Ensure you set the GROQ_API_KEY in your system environment or terminal before testing:
    # export GROQ_API_KEY="your-groq-key"
    dummy_audio_path = "/home/ubuntu/AI-Shorts-Bot/transcripts/dummy_audio.mp3"
    transcribed_file_path = transcribe_audio(dummy_audio_path)
    if transcribed_file_path:
        print(f"Audio transcribed to: {transcribed_file_path}")
    else:
        print("Audio transcription failed.")
                     
