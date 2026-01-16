"""
Core Routes - Serves the main Launchpad dashboard
"""

import os
from flask import Blueprint, render_template

# Get the directory where this file is located
CORE_DIR = os.path.dirname(os.path.abspath(__file__))

core_bp = Blueprint('core', __name__,
                    template_folder=os.path.join(CORE_DIR, 'templates'),
                    static_folder=os.path.join(CORE_DIR, 'static'),
                    static_url_path='/static')


# Experiment Registry - Add new experiments here
EXPERIMENTS = [
    {
        'id': 'tts',
        'name': "Don't Pay For ElevenLabs",
        'description': 'Neural text-to-speech with 300+ voices. Transform any text into natural speech instantly.',
        'icon': '🎙️',
        'url': '/experiments/tts/',
        'status': 'live',
        'tags': ['Voice AI', 'Neural TTS', 'Edge']
    },
    {
        'id': 'daily-planner',
        'name': "Don't Pay For Spark Mail",
        'description': 'AI Executive Assistant. Connects to Gmail to prioritize your day and generate a briefing.',
        'icon': '📧',
        'url': '/experiments/planner/',
        'status': 'live',
        'tags': ['Productivity', 'Gmail', 'AI Agent']
    },
    {
        'id': 'youtube-summarizer',
        'name': "Don't Pay for Eightify",
        'description': 'YouTube video summarizer. Turns learning content into concise bullet points.',
        'icon': '📺',
        'url': '/experiments/youtube-summarizer/',
        'status': 'live',
        'tags': ['Video AI', 'Summarization', 'Learning']
    },
    {
        'id': 'coming-soon-1',
        'name': 'Voice Cloner',
        'description': 'Clone any voice with just 3 seconds of audio. Create custom voice profiles.',
        'icon': '🎭',
        'url': '#',
        'status': 'coming',
        'tags': ['Voice AI', 'Cloning']
    },
    {
        'id': 'coming-soon-2',
        'name': 'Audio Transcriber',
        'description': 'Whisper-powered transcription with speaker diarization and timestamps.',
        'icon': '📝',
        'url': '#',
        'status': 'coming',
        'tags': ['Whisper', 'STT']
    },
    {
        'id': 'coming-soon-3',
        'name': 'AI Image Lab',
        'description': 'Generate, edit, and transform images with state-of-the-art diffusion models.',
        'icon': '🎨',
        'url': '#',
        'status': 'coming',
        'tags': ['Diffusion', 'Gen AI']
    }
]


@core_bp.route('/')
def index():
    """Render the main launchpad dashboard"""
    return render_template('index.html', experiments=EXPERIMENTS)
