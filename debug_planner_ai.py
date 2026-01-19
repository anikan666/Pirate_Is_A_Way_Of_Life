import os
import logging
from experiments.daily_planner.ai_service import generate_plan
from config import Config

# Configure logging to see output
logging.basicConfig(level=logging.DEBUG)

print(f"LLM Provider: {Config.LLM_PROVIDER}")
print(f"Model Name: {Config.LLM_MODEL_NAME}")
print(f"Anthropic Key Present: {bool(Config.ANTHROPIC_API_KEY)}")

prompt = """
INPUT EMAILS:
EMAIL #1:
- From: Boss
- Subject: Urgent Project
- BODY: Please finish the report by EOD.

RULES:
1. Output ONLY valid JSON.
2. Structure: { "summary": "...", "tasks": [] }

Output ONLY valid JSON:
"""

print("\nRunning generate_plan...")
result = generate_plan(prompt)

if result:
    print("\nSUCCESS! Plan generated:")
    print(result)
else:
    print("\nFAILURE! Plan was None.")
