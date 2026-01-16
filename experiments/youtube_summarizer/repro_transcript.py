import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiments.youtube_summarizer.services.youtube_service import get_video_transcript
import traceback

urls = [
    "https://www.youtube.com/watch?v=jNQXAC9IVRw", # Me at the zoo (short, likely has transcript)
]

print("Starting reproduction test...")

for url in urls:
    print(f"\nTesting URL: {url}")
    try:
        res = get_video_transcript(url)
        print("Success! Transcript length:", len(res['full_text']))
    except Exception:
        print("Caught Exception:")
        traceback.print_exc()
