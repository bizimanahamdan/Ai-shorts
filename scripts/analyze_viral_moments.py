import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)


def analyze_viral_moments(transcript_path, video_duration_seconds, output_analysis_path="/home/ubuntu/AI-Shorts-Bot/clips/"):
    """
    Analyzes a video transcript using Google Gemini to identify viral moments.
    Args:
        transcript_path (str): The path to the input transcript file (SRT format).
        video_duration_seconds (int): The total duration of the video in seconds.
        output_analysis_path (str): The directory where the analysis will be saved.
    Returns:
        str: The path to the generated JSON analysis file, or None if analysis fails.
    """
    if not os.path.exists(output_analysis_path):
        os.makedirs(output_analysis_path)

    transcript_filename = os.path.basename(transcript_path)
    analysis_filename = os.path.splitext(transcript_filename)[0] + "_viral_moments.json"
    full_output_analysis_path = os.path.join(output_analysis_path, analysis_filename)

    try:
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')

        with open(transcript_path, "r") as f:
            transcript_content = f.read()

        prompt = f"""
        You are an expert video editor and content strategist. Your task is to analyze the provided video transcript and identify the most engaging, viral-worthy moments suitable for short-form video platforms like TikTok, Instagram Reels, and YouTube Shorts.

        The video has a total duration of {video_duration_seconds} seconds.

        Transcript (SRT format):
        ```
        {transcript_content}
        ```

        Identify between 3 and 6 distinct viral moments. For each moment, provide:
        1.  A brief, catchy title for the short.
        2.  The start time (in seconds) of the engaging segment.
        3.  The end time (in seconds) of the engaging segment.
        4.  A short explanation of why this moment is viral-worthy (e.g., strong hook, emotional peak, surprising revelation, key takeaway).
        5.  Relevant keywords/hashtags.
        6.  A suggested emoji to represent the moment.

        Each short should be between 20 and 60 seconds long. Ensure the start and end times are precise.

        Return the output as a JSON array of objects, where each object represents a viral moment. Example format:
        [
            {{
                "title": "Catchy Title 1",
                "start_time_seconds": 120,
                "end_time_seconds": 150,
                "reason": "This moment features a strong emotional appeal and a clear call to action.",
                "hashtags": ["#motivation", "#inspiration", "#success"],
                "emoji": "🔥"
            }},
            {{
                "title": "Catchy Title 2",
                "start_time_seconds": 200,
                "end_time_seconds": 245,
                "reason": "A surprising twist is revealed, creating high suspense.",
                "hashtags": ["#mystery", "#shocking", "#reveal"],
                "emoji": "🤯"
            }}
        ]
        """

        logger.info(f"Analyzing transcript for viral moments: {transcript_path}")
        response = model.generate_content(prompt)

        json_string = response.text.strip()
        if json_string.startswith("```json") and json_string.endswith("```"):
            json_string = json_string[7:-3].strip()
        elif json_string.startswith("```") and json_string.endswith("```"):
            json_string = json_string[3:-3].strip()

        with open(full_output_analysis_path, "w") as f:
            f.write(json_string)

        logger.info(f"Viral moments analysis saved to: {full_output_analysis_path}")
        return full_output_analysis_path

    except Exception as e:
        logger.error(f"Error during viral moments analysis: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dummy_transcript_path = "/home/ubuntu/AI-Shorts-Bot/transcripts/dummy_transcript.srt"
    if not os.path.exists(os.path.dirname(dummy_transcript_path)):
        os.makedirs(os.path.dirname(dummy_transcript_path))

    dummy_srt_content = """1
00:00:00,000 --> 00:00:05,000
Hello everyone, and welcome to this amazing video.

2
00:00:05,500 --> 00:00:10,000
Today, we're going to talk about something truly groundbreaking.

3
00:00:10,500 --> 00:00:15,000
Many people struggle with this, but I have a secret to share.
"""
    with open(dummy_transcript_path, "w") as f:
        f.write(dummy_srt_content)

    video_duration = 45
    analysis_file = analyze_viral_moments(dummy_transcript_path, video_duration)
    if analysis_file:
        print(f"Analysis completed: {analysis_file}")
    else:
        print("Analysis failed.")
