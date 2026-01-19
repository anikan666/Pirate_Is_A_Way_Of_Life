from experiments.youtube_summarizer.services.youtube_service import get_video_transcript
import traceback

url = "https://www.youtube.com/watch?v=TlhN3_yPpnM"
print(f"Testing transcript fetch for: {url}")

try:
    result = get_video_transcript(url)
    print("Success!")
    print(f"Video ID: {result['video_id']}")
    print(f"Transcript Length: {len(result['full_text'])} chars")
    print("First 100 chars:", result['full_text'][:100])
except Exception:
    traceback.print_exc()
