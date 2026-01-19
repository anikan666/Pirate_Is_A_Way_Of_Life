from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from urllib.parse import urlparse, parse_qs
import re
import requests
import json
import logging
import os

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

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

def fetch_transcript_with_ytdlp(video_url):
    """
    Fallback method to fetch transcript using yt-dlp.
    Useful when youtube-transcript-api is blocked (429/IP ban).
    """
    if not yt_dlp:
        raise ImportError("yt_dlp is not installed")

    logger.info(f"Attempting to fetch transcript with yt-dlp for {video_url}")
    
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en', 'en-US'],
        'quiet': True,
        'no_warnings': True,
    }
    


    # Check for cookies.txt
    cookies_file = 'cookies.txt'
    if os.path.exists(cookies_file):
        ydl_opts['cookiefile'] = cookies_file
        logger.info(f"Using cookies from {cookies_file} for yt-dlp")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
        except Exception as e:
            raise Exception(f"yt-dlp failed to extract info: {str(e)}")

        # Check for subtitles
        subtitles = info.get('subtitles', {}) or {}
        automatic_captions = info.get('automatic_captions', {}) or {}
        
        # Merge dicts
        all_subs = {**automatic_captions, **subtitles}
        
        if not all_subs:
             raise ValueError("No subtitles found via yt-dlp")
             
        # Look for English
        # Prioritize 'en', then 'en-US', then any 'en-'
        lang_code = None
        for code in ['en', 'en-US', 'en-orig', 'en-GB']:
            if code in all_subs:
                lang_code = code
                break
        
        if not lang_code:
            # Search for any english
            for code in all_subs.keys():
                if code.startswith('en'):
                    lang_code = code
                    break
        
        if not lang_code:
             # Fallback to first available
             lang_code = list(all_subs.keys())[0]

        logger.info(f"Found subtitles in language: {lang_code}")
        subs_list = all_subs[lang_code]
        
        # Prefer json3 (rich metadata) > vtt > others
        sub_url = next((s['url'] for s in subs_list if s.get('ext') == 'json3'), None)
        is_json = True
        
        if not sub_url:
             # Fallback to vtt or srv3
             # Note: simple requests.get on vtt url works
             sub_url = next((s['url'] for s in subs_list if s.get('ext') == 'vtt'), None)
             is_json = False # We won't parse VTT manually here for simplicity unless needed, 
                             # but json3 is standard for youtube.
             
        if not sub_url:
             sub_url = subs_list[0]['url']
        
        # Fetch the content
        try:
            res = requests.get(sub_url)
            res.raise_for_status()
            content = res.text
        except Exception as e:
            raise Exception(f"Failed to download subtitle track: {str(e)}")
        
        transcript = []
        
        if is_json or 'json3' in sub_url:
            try:
                data = json.loads(content)
                events = data.get('events', [])
                for event in events:
                    # 'segs' contains the text parts
                    if 'segs' in event and event['segs']:
                        text = "".join([s.get('utf8', '') for s in event['segs']])
                        # tStartMs is start time in ms
                        start = float(event.get('tStartMs', 0)) / 1000.0
                        
                        # Clean up text (remove newlines, etc)
                        text = text.replace('\n', ' ').strip()
                        if text:
                            transcript.append({'text': text, 'start': start})
            except json.JSONDecodeError:
                raise Exception("Failed to parse JSON3 transcript")
        else:
            # Determine if it's actually JSON content despite extension?
            # Or implement VTT parser?
            # For now, let's assume we get JSON3 as it's the default internal format ytdlp exposes.
            # If we hit this, we might fail, but it's a fallback.
            raise Exception(f"Unsupported subtitle format url: {sub_url}")

        return transcript



def fetch_transcript_with_notegpt(video_id):
    """
    Attempts to fetch transcript using NoteGPT's public API.
    This acts as a proxy to bypass YouTube's direct blocking.
    """
    url = "https://notegpt.io/api/v2/video-transcript"
    params = {
        "platform": "youtube",
        "video_id": video_id
    }
    # Headers mimicking a real browser visiting NoteGPT
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://notegpt.io/youtube-transcript-generator",
        "Origin": "https://notegpt.io",
        "Accept": "application/json, text/plain, */*"
    }

    try:
        logger.info(f"Attempting to fetch transcript via NoteGPT for {video_id}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"NoteGPT API returned status {response.status_code}")
            return None
            
        data = response.json()
        
        transcript_segments = []
        
        # Check if the response matches expected structure
        items = data.get('data', [])
        if not items and isinstance(data, list):
            items = data
            
        if not items:
             logger.warning("NoteGPT returned empty transcript data")
             return None

        # Transform to our internal format
        for item in items:
            text = item.get('text') or item.get('content') or ""
            start = item.get('start') or item.get('startTime') or 0
            
            # Ensure numbers
            try:
                start = float(start)
            except (ValueError, TypeError):
                start = 0.0
                
            if text:
                transcript_segments.append({
                    'text': text,
                    'start': start
                })
                
        if not transcript_segments:
            logger.warning("Could not parse NoteGPT transcript format")
            return None
            
        logger.info(f"Successfully fetched {len(transcript_segments)} segments from NoteGPT")
        return transcript_segments

    except Exception as e:
        logger.error(f"NoteGPT fetch failed: {str(e)}")
        return None


def get_video_transcript(video_url):
    """
    Fetches transcript for a given YouTube URL.
    Returns a dictionary with 'text' (combined for LLM) and 'metadata' (raw segments).
    Robustly handles different versions of youtube_transcript_api and falls back to yt-dlp.
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    full_transcript = None
    last_error = None

    # --- Attempt 0: NoteGPT Proxy (Best for bypassing IP blocks) ---
    try:
        full_transcript = fetch_transcript_with_notegpt(video_id)
    except Exception as e:
        logger.error(f"NoteGPT strategy failed: {e}")

    # --- Attempt 1: youtube_transcript_api ---
    if not full_transcript:
        try:
            cookies_file = 'cookies.txt'
            cookies_path = cookies_file if os.path.exists(cookies_file) else None
            if cookies_path:
                 logger.info(f"Using cookies from {cookies_path} for youtube_transcript_api")

            # Strategy 1a: Try standard static method (newer versions)
            if hasattr(YouTubeTranscriptApi, 'get_transcript'):
                try:
                    # Note: 'cookies' param requires a file path in newer versions
                    kwargs = {'languages': ['en', 'en-US']}
                    if cookies_path:
                        kwargs['cookies'] = cookies_path
                    full_transcript = YouTubeTranscriptApi.get_transcript(video_id, **kwargs)
                except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
                    try:
                        full_transcript = YouTubeTranscriptApi.get_transcript(video_id)
                    except Exception:
                        pass
            
            # Strategy 1b: Instance method (older/custom versions)
            if not full_transcript:
                try:
                    api = YouTubeTranscriptApi()
                    if hasattr(api, 'fetch'):
                         try:
                             # Old versions might not support cookies easily this way, but let's try standard fetch
                             full_transcript = api.fetch(video_id, languages=['en', 'en-US'])
                         except Exception:
                             full_transcript = api.fetch(video_id)
                except Exception:
                    pass
                    
        except Exception as e:
            last_error = e
            logger.error(f"youtube_transcript_api failed: {str(e)}")
            print(f"youtube_transcript_api failed: {e}")

    # --- Attempt 2: yt-dlp Fallback ---
    if not full_transcript:
        print("Falling back to yt-dlp...")
        try:
            full_transcript = fetch_transcript_with_ytdlp(video_url)
        except Exception as e:
            print(f"yt-dlp failed: {e}")
            if last_error:
                raise last_error # Raise original error if both fail
            raise ValueError(f"Could not retrieve transcript: {str(e)}")

    if not full_transcript:
         raise ValueError("Could not fetch transcript (empty result)")
    
    # Format for LLM: "[MM:SS] Text segment"
    formatted_text_parts = []
    
    for entry in full_transcript:
        start_time = 0
        text_content = ""
        
        # Handle Dictionary (standard & yt-dlp)
        if isinstance(entry, dict):
            start_time = entry.get('start', 0)
            text_content = entry.get('text', '')
        # Handle Object (custom library versions)
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
