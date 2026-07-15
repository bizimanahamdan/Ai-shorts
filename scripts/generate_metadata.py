import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)


def generate_metadata(viral_moments_json_path, output_metadata_path="/home/ubuntu/AI-Shorts-Bot/exports/"):
    """
    Generates titles, descriptions, and hashtags for viral moments using Google Gemini.
    Args:
        viral_moments_json_path (str): Path to the JSON file with viral moments data.
        output_metadata_path (str): Directory to save the metadata JSON.
    Returns:
        str: Path to the generated metadata file, or None if generation fails.
    """
    if not os.path.exists(output_metadata_path):
        os.makedirs(output_metadata_path)

    moments_filename = os.path.basename(viral_moments_json_path)
    metadata_filename = os.path.splitext(moments_filename)[0] + "_metadata.json"
    full_output_metadata_path = os.path.join(output_metadata_path, metadata_filename)

    try:
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')

        with open(viral_moments_json_path, "r") as f:
            viral_moments = json.load(f)

        if not viral_moments:
            logger.warning("No viral moments data found.")
            return None

        moment = viral_moments[0] if isinstance(viral_moments, list) else viral_moments

        prompt = f"""
        You are a social media content expert. Based on the following viral moment data, generate optimized metadata for a short-form video post.

        Viral Moment Data:
        - Title: {moment.get("title", "Unknown")}
        - Reason for virality: {moment.get("reason", "Engaging content")}
        - Hashtags from analysis: {moment.get("hashtags", [])}
        - Emoji: {moment.get("emoji", "")}

        Generate the following:
        Title (short, catchy, under 100 characters, engaging, includes keywords, encourages views):
        Description (150-300 characters, engaging, includes keywords, encourages views):
        Hashtags (5-10 relevant, trending hashtags, comma-separated):
        Return the output as a JSON object with keys: "title", "description", "hashtags".
        Example:
        {{
            "title": "This is a Click-Worthy Title! 🔥",
            "description": "You won't believe what happens next! Watch now to find out the secret to success. #viral #motivation #shorts",
            "hashtags": "#viralshorts, #motivation, #inspiration, #success, #lifetips"
        }}
        """

        logger.info(f"Generating metadata for viral moment: {moment.get('title', 'Unknown')}")
        response = model.generate_content(prompt)
        json_string = response.text.strip()

        if json_string.startswith("```json") and json_string.endswith("```"):
            json_string = json_string[7:-3].strip()
        elif json_string.startswith("```") and json_string.endswith("```"):
            json_string = json_string[3:-3].strip()

        with open(full_output_metadata_path, "w") as f:
            f.write(json_string)

        logger.info(f"Metadata generated and saved to: {full_output_metadata_path}")
        return full_output_metadata_path

    except Exception as e:
        logger.error(f"Error during metadata generation: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("generate_metadata.py - Use generate_metadata() with a viral moments JSON path.")
