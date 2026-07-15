import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


def transcribe_audio(audio_path, output_transcript_path="/home/ubuntu/AI-Shorts-Bot/transcripts/"):
    """
    Transcribes an audio file using OpenAI Whisper API.
    Args:
        audio_path (str): The path to the input audio file.
        output_transcript_path (str): The directory where the transcript will be saved.
    Returns:
        str: The path to the generated transcript file (SRT format), or None if transcription fails.
    """
    if not os.path.exists(output_transcript_path):
        os.makedirs(output_transcript_path)

    audio_filename = os.path.basename(audio_path)
    transcript_filename = os.path.splitext(audio_filename)[0] + ".srt"
    full_output_transcript_path = os.path.join(output_transcript_path, transcript_filename)

    try:
        client = OpenAI()

        with open(audio_path, "rb") as audio_file:
            logger.info(f"Transcribing audio file: {audio_path}")
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="srt"
            )

        with open(full_output_transcript_path, "w") as f:
            f.write(transcript)

        logger.info(f"Transcription successful. Saved to: {full_output_transcript_path}")
        return full_output_transcript_path

    except Exception as e:
        logger.error(f"Error during audio transcription: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dummy_audio_path = "/home/ubuntu/AI-Shorts-Bot/transcripts/dummy_audio.mp3"
    transcribed_file_path = transcribe_audio(dummy_audio_path)
    if transcribed_file_path:
        print(f"Audio transcribed to: {transcribed_file_path}")
    else:
        print("Audio transcription failed.")
