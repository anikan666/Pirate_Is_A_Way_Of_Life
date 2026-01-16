from flask import Blueprint, render_template, request, jsonify
import os

from .services.youtube_service import get_video_transcript
from .services.llm_service import summarize_content, chat_answer

youtube_bp = Blueprint('youtube_summarizer', __name__, template_folder='templates', static_folder='static')

# Simple in-memory cache: {video_url: transcript_text}
# In production, use Redis or a database
TRANSCRIPT_CACHE = {}

@youtube_bp.route('/')
def index():
    return render_template('youtube_summarizer.html')

@youtube_bp.route('/summarize', methods=['POST'])
def summarize():
    data = request.json
    video_url = data.get('url')
    
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
        
    try:
        # 1. Get Transcript
        # Check cache first
        if video_url in TRANSCRIPT_CACHE:
             transcript_text = TRANSCRIPT_CACHE[video_url]['full_text']
             video_id = TRANSCRIPT_CACHE[video_url]['video_id']
        else:
            transcript_data = get_video_transcript(video_url)
            transcript_text = transcript_data['full_text']
            video_id = transcript_data['video_id']
            TRANSCRIPT_CACHE[video_url] = transcript_data
        
        # 2. Generate Summary
        summary = summarize_content(transcript_text)
        
        return jsonify({
            'status': 'success',
            'video_id': video_id,
            'summary': summary,
            'transcript': transcript_text
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Log the full error in production
        print(f"Error: {e}")
        return jsonify({'error': 'Failed to process video'}), 500

@youtube_bp.route('/chat', methods=['POST'])
def chat():
    data = request.json
    video_url = data.get('url')
    user_message = data.get('message')
    history = data.get('history', [])
    
    if not video_url or not user_message:
        return jsonify({'error': 'Missing data'}), 400
        
    try:
        # 1. Get Transcript (must use cache or fetch)
        if video_url in TRANSCRIPT_CACHE:
             transcript_text = TRANSCRIPT_CACHE[video_url]['full_text']
        else:
             # Just in case user reloaded page and cache cleared (server restart)
             transcript_data = get_video_transcript(video_url)
             transcript_text = transcript_data['full_text']
             TRANSCRIPT_CACHE[video_url] = transcript_data
             
        # 2. Generate Answer
        answer = chat_answer(transcript_text, history, user_message)
        
        return jsonify({
            'status': 'success',
            'answer': answer
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Failed to answer'}), 500


