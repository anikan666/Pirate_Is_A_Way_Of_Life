from youtube_transcript_api import YouTubeTranscriptApi

print("Inspecting fetch return type...")
try:
    api = YouTubeTranscriptApi()
    res = api.fetch("jNQXAC9IVRw", languages=['en'])
    print(f"Type of result: {type(res)}")
    print(f"Length: {len(res)}")
    if len(res) > 0:
        first = res[0]
        print(f"Type of first item: {type(first)}")
        print(f"First item: {first}")
except Exception as e:
    print(f"Error: {e}")
