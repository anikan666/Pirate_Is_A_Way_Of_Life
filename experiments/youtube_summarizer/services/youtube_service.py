from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

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

    # Try fetching transcript with fallback mechanisms
    full_transcript = None
    
    # Method 1: Static get_transcript (Standard)
    if hasattr(YouTubeTranscriptApi, 'get_transcript'):
        try:
            full_transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
        except Exception:
            # Try without languages if that failed
            try:
                full_transcript = YouTubeTranscriptApi.get_transcript(video_id)
            except Exception:
                pass
    
    # Method 2: Instance-based fetch (Older versions)
    if not full_transcript:
        try:
            # Some older versions operate via an instance
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Try to find English manually
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US']) 
            except:
                # Fallback to any transcript
                transcript = next(iter(transcript_list))
            
            full_transcript = transcript.fetch()
        except AttributeError:
             # If list_transcripts doesn't exist, try direct fetch on instance
             try:
                 api = YouTubeTranscriptApi()
                 if hasattr(api, 'fetch'):
                     try:
                         full_transcript = api.fetch(video_id, languages=['en', 'en-US'])
                     except:
                         full_transcript = api.fetch(video_id)
                 elif hasattr(api, 'get_transcript'):
                     full_transcript = api.get_transcript(video_id)
             except Exception as e:
                 logger.warning(f"Instance fetch failed: {e}")
        except Exception as e:
            logger.warning(f"Secondary fetch method failed: {e}")

    if not full_transcript:
        # Last ditch: maybe it IS a static method but failed previously?
        # Re-raise the original error if we really can't find it, but let's try one more naked call if we haven't
        if not hasattr(YouTubeTranscriptApi, 'get_transcript'):
             pass # We can't do anything more
        pass

    if not full_transcript:
         raise ValueError("Could not fetch transcript (empty result)")
    
    # Format for LLM: "[MM:SS] Text segment"
    formatted_text_parts = []
    
    for entry in full_transcript:
        start_time = 0
        text_content = ""
        
        # Handle Dictionary (standard)
        if isinstance(entry, dict):
            start_time = entry.get('start', 0)
            text_content = entry.get('text', '')
        # Handle Object (older versions)
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
