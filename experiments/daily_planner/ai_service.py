"""
AI Service Module for Daily Planner

Provides LLM integration with support for multiple providers:
- Anthropic Claude
- Google Gemini  
- Local Ollama

Usage:
    from ai_service import generate_plan
    plan_data = generate_plan(prompt)
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_provider() -> str:
    """Get the configured LLM provider from environment."""
    from config import Config
    return Config.LLM_PROVIDER.lower()


def clean_json_response(text: str) -> str:
    """Strip markdown code blocks and preamble from LLM response."""
    import re
    # Remove markdown code blocks
    text = text.replace('```json', '').replace('```', '')
    
    # regex to find the first '{' and last '}'
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)
        
    return text.strip()


def generate_with_anthropic(prompt: str, system_prompt: str = None) -> dict:
    """
    Generate content using Anthropic Claude.
    
    Args:
        prompt: The user prompt to send
        system_prompt: System instruction for the model
        
    Returns:
        Parsed JSON response as dict
        
    Raises:
        Exception: If API key is missing or API call fails
    """
    import anthropic
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise Exception("ANTHROPIC_API_KEY not found in environment variables.")
    
    from config import Config
    
    client = anthropic.Anthropic(api_key=api_key)
    
    if system_prompt is None:
        system_prompt = """You are an elite Executive Assistant.
<instructions>
1. Analyze the input emails carefully.
2. Output ONLY valid JSON matching the requested structure.
3. Do NOT include any preamble, markdown formatting, or explanation.
4. If no tasks are found, return empty lists.
</instructions>
"""

    message = client.messages.create(
        model=Config.LLM_MODEL_NAME,
        max_tokens=4096,
        temperature=0,
        system=system_prompt,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    clean_text = clean_json_response(message.content[0].text)
    result = json.loads(clean_text)
    logger.info(f"Successfully generated plan with Anthropic {Config.LLM_MODEL_NAME}!")
    return result


def generate_with_gemini(prompt: str) -> dict:
    """
    Generate content using Google Gemini.
    
    Tries multiple model versions in order of preference.
    
    Args:
        prompt: The user prompt to send
        
    Returns:
        Parsed JSON response as dict
        
    Raises:
        Exception: If API key is missing or all models fail
    """
    import google.generativeai as genai
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise Exception("GEMINI_API_KEY not found in environment variables.")
    
    genai.configure(api_key=api_key)
    
    # Models to try in order of preference
    candidates = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-001',
        'gemini-1.5-pro',
        'gemini-2.0-flash-exp',
        'gemini-pro'
    ]
    
    response = None
    last_error = None
    
    for model_name in candidates:
        try:
            logger.debug(f"Attempting to use model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            break  # Success!
        except Exception as e:
            logger.debug(f"Failed with {model_name}: {e}")
            last_error = e
    
    if not response:
        raise last_error
    
    clean_text = clean_json_response(response.text)
    result = json.loads(clean_text)
    logger.info("Successfully generated plan with Google Gemini!")
    return result


def generate_with_ollama(prompt: str, model: str = "llama3") -> dict:
    """
    Generate content using local Ollama instance.
    
    Args:
        prompt: The user prompt to send
        model: Ollama model name (default: llama3)
        
    Returns:
        Parsed JSON response as dict
        
    Raises:
        Exception: If Ollama request fails
    """
    import requests
    
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        },
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"Ollama returned error: {response.status_code}")
    
    result = response.json()
    plan_data = json.loads(result['response'])
    logger.info("Successfully generated plan with Local LLM (Ollama)!")
    return plan_data


def generate_plan(prompt: str) -> Optional[dict]:
    """
    Generate a plan from the given prompt using the configured LLM provider.
    
    Automatically selects provider based on LLM_PROVIDER environment variable.
    Falls back gracefully if provider fails, returning None.
    
    Args:
        prompt: The user prompt containing email data and instructions
        
    Returns:
        Parsed JSON plan as dict, or None if generation fails
    """
    provider = get_provider()
    logger.info(f"Using AI Provider: {provider}")
    
    try:
        if provider == 'anthropic':
            return generate_with_anthropic(prompt)
        elif provider == 'gemini':
            return generate_with_gemini(prompt)
        else:
            return generate_with_ollama(prompt)
            
    except Exception as e:
        import traceback
        logger.error(f"\n{'='*60}")
        logger.error(f"AI Generation Error ({provider})")
        logger.error(f"Error Type: {type(e).__name__}")
        logger.error(f"Error Message: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error(f"{'='*60}\n")
        
        # Also print for debug visibility
        print(f"\n{'='*60}")
        print(f"AI Generation Error ({provider})")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        print(f"Traceback:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        # Return error details instead of None so UI can show it
        return {
            "error": "AI Generation Failed",
            "details": str(e),
            "provider": provider,
            "tasks": [],     # Empty default
            "schedule": [],  # Empty default
            "summary": f"Error: {str(e)}"
        }
