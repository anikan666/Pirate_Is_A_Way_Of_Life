from youtube_transcript_api import YouTubeTranscriptApi
import traceback

print("Testing static fetch:")
try:
    # Try static
    res = YouTubeTranscriptApi.fetch("jNQXAC9IVRw", languages=['en'])
    print("Static fetch success!")
except Exception:
    print("Static fetch failed")
    traceback.print_exc()

print("\nTesting instance fetch:")
try:
    api = YouTubeTranscriptApi()
    res = api.fetch("jNQXAC9IVRw", languages=['en'])
    print("Instance fetch success!")
except Exception:
    print("Instance fetch failed")
    traceback.print_exc()
