from youtube_transcript_api import YouTubeTranscriptApi
import traceback

try:
    print("Instantiating...")
    api = YouTubeTranscriptApi()
    
    print("Fetching...")
    # Trying the code exactly as in youtube_service.py
    transcript = api.fetch("zfA8sF2_QM8", languages=['en', 'en-US'])
    
    print("Success!")
    print(transcript[0]) # print first segment
    
except Exception:
    traceback.print_exc()
