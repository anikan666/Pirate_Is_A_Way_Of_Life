from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
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
    Robustly handles different versions of youtube_transcript_api.
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    try:
        full_transcript = None
        
        # Strategy 1: Try standard static method (newer versions)
        if hasattr(YouTubeTranscriptApi, 'get_transcript'):
            try:
                full_transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
            except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
                try:
                    full_transcript = YouTubeTranscriptApi.get_transcript(video_id)
                except Exception:
                    pass
        
        # Strategy 2: If failed or not available, try instance method (older/custom versions)
        if full_transcript is None:
            try:
                # Some versions require instantiation
                api = YouTubeTranscriptApi()
                if hasattr(api, 'fetch'):
                     try:
                         full_transcript = api.fetch(video_id, languages=['en', 'en-US'])
                     except Exception:
                         full_transcript = api.fetch(video_id)
            except Exception as e:
                # If both strategies fail, raise the last exception
                 if not full_transcript:
                     raise e

        if not full_transcript:
             raise ValueError("Could not fetch transcript (empty result)")
        
        # Format for LLM: "[MM:SS] Text segment"
        # Handle both Dictionary (standard) and Object (custom) items
        formatted_text_parts = []
        
        for entry in full_transcript:
            start_time = 0
            text_content = ""
            
            # Handle Dictionary
            if isinstance(entry, dict):
                start_time = entry.get('start', 0)
                text_content = entry.get('text', '')
            # Handle Object (has attributes)
            else:
                start_time = getattr(entry, 'start', 0)
                text_content = getattr(entry, 'text', '')
                
            timestamp = format_timestamp(start_time)
            formatted_text_parts.append(f"[{timestamp}] {text_content}")
            
        return {
            "video_id": video_id,
            "full_text": "\n".join(formatted_text_parts),
            "segments": full_transcript
        }

    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise ValueError("No transcript found for this video.")
    except Exception as e:
        raise Exception(f"Could not retrieve transcript: {str(e)}")
