from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import re

def extract_video_id(url):
    """
    Extracts video ID from various YouTube URL formats.
    """
    # handle short links
    if 'youtu.be' in url:
        return url.split('/')[-1].split('?')[0]
    
    # handle standard links
    parsed = urlparse(url)
    if 'youtube.com' in parsed.netloc:
        if 'v' in parse_qs(parsed.query):
            return parse_qs(parsed.query)['v'][0]
            
    # handle failures
    return None

def format_timestamp(seconds):
    """
    Converts seconds to MM:SS format.
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def get_video_transcript(video_url):
    """
    Fetches transcript for a given YouTube URL.
    Returns a dictionary with 'text' (combined for LLM) and 'metadata' (raw segments).
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    try:
        # Instantiate the API (required for this version)
        yt_api = YouTubeTranscriptApi()
        
        # Fetch transcript directly
        # fetch(video_id, languages=['en'])
        try:
            full_transcript = yt_api.fetch(video_id, languages=['en', 'en-US'])
        except Exception:
             # Fallback to default (usually auto-generated or first available)
             full_transcript = yt_api.fetch(video_id)
        
        # Format for LLM: "[MM:SS] Text segment"
        formatted_text_parts = []
        for entry in full_transcript:
            # Handle both objects (this version) and dicts (standard version) just in case
            if hasattr(entry, 'start'):
                start_time = entry.start
                text_content = entry.text
            else:
                start_time = entry['start']
                text_content = entry['text']
                
            timestamp = format_timestamp(start_time)
            formatted_text_parts.append(f"[{timestamp}] {text_content}")
            
        return {
            "video_id": video_id,
            "full_text": "\n".join(formatted_text_parts),
            "segments": full_transcript # valid for frontend "click to seek" if needed later
        }

    except Exception as e:
        raise Exception(f"Could not retrieve transcript: {str(e)}")
