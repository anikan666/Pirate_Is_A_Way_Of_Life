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
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    try:
        # standard usage of youtube_transcript_api
        try:
            full_transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
             # Try default/auto-generated
            full_transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Format for LLM: "[MM:SS] Text segment"
        formatted_text_parts = []
        for entry in full_transcript:
            # Entry is a dictionary in the standard library
            # keys are 'text', 'start', 'duration'
            start_time = entry.get('start', 0)
            text_content = entry.get('text', '')
                
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
