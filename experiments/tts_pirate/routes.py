"""
TTS Pirate - Text-to-Speech Experiment Routes
Uses Edge-TTS (online neural voices) for web deployment
NO pyttsx3 - this is web-deployable
"""

import os
from flask import Blueprint, render_template, request, jsonify, send_file, Response
from dotenv import load_dotenv
import edge_tts
import asyncio
import re
import uuid
import html
import io
import threading
import time
from datetime import datetime

# Load environment variables
load_dotenv()

# Get the directory where this file is located
TTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Create Blueprint with explicit paths
tts_bp = Blueprint('tts', __name__, 
                   template_folder=os.path.join(TTS_DIR, 'templates'),
                   static_folder=os.path.join(TTS_DIR, 'static'),
                   static_url_path='/experiments/tts/static')

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = os.environ.get('BASE_URL', '').rstrip('/')
STORAGE_TYPE = os.environ.get('STORAGE_TYPE', 'local').lower()
FILE_MAX_AGE_SECONDS = int(os.environ.get('FILE_MAX_AGE_SECONDS', 3600))

# Import storage backend
from storage import get_storage_backend, LocalStorage
storage = get_storage_backend()

# Input Validation Constants
MAX_TEXT_LENGTH = 5000
MAX_FILENAME_LENGTH = 100

# =============================================================================
# AUTO-CLEANUP BACKGROUND THREAD
# =============================================================================

def cleanup_old_files():
    """Background thread to clean up files older than FILE_MAX_AGE_SECONDS"""
    while True:
        try:
            current_time = time.time()
            files = storage.list_files()
            
            for file in files:
                file_age = current_time - file['created']
                if file_age > FILE_MAX_AGE_SECONDS:
                    storage.delete_file(file['filename'])
                    print(f"Auto-deleted old file: {file['filename']} (age: {int(file_age)}s)")
            
            if hasattr(storage, 'cleanup_temp_files'):
                storage.cleanup_temp_files(max_age_seconds=300)
                
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        time.sleep(300)


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

# =============================================================================
# INPUT VALIDATION HELPERS
# =============================================================================

def sanitize_text(text):
    """Sanitize input text for TTS processing"""
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if len(text) == 0 or len(text) > MAX_TEXT_LENGTH:
        return None
    text = html.escape(text)
    return text


def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal and injection"""
    if not filename or not isinstance(filename, str):
        return None
    filename = os.path.basename(filename)
    if len(filename) == 0 or len(filename) > MAX_FILENAME_LENGTH:
        return None
    name, ext = os.path.splitext(filename)
    if ext.lower() not in ['.mp3', '.wav']:
        return None
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_name:
        return None
    return safe_name + ext


def validate_voice_id(voice_id):
    """Validate voice ID format"""
    if not voice_id or not isinstance(voice_id, str):
        return None
    if not re.match(r'^[a-zA-Z0-9\-_]+$', voice_id):
        return None
    if len(voice_id) > 100:
        return None
    return voice_id


def validate_numeric_param(value, min_val, max_val, default):
    """Validate and clamp numeric parameters"""
    try:
        value = int(value)
        return max(min_val, min(max_val, value))
    except (TypeError, ValueError):
        return default


# =============================================================================
# TTS FUNCTIONALITY - EDGE TTS ONLY (ONLINE, WEB-DEPLOYABLE)
# =============================================================================

edge_voices_cache = None


async def get_edge_voices_async():
    """Get list of available Edge TTS voices"""
    voices = await edge_tts.list_voices()
    voice_list = []
    for voice in voices:
        voice_list.append({
            'id': voice['ShortName'],
            'name': f"{voice['ShortName']} ({voice['Locale']})",
            'display_name': voice.get('FriendlyName', voice['ShortName']),
            'type': 'edge',
            'locale': voice['Locale'],
            'gender': voice['Gender']
        })
    return voice_list


def get_edge_voices():
    """Synchronous wrapper for getting Edge TTS voices"""
    global edge_voices_cache
    if edge_voices_cache is not None:
        return edge_voices_cache
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        edge_voices_cache = loop.run_until_complete(get_edge_voices_async())
        loop.close()
        return edge_voices_cache
    except Exception as e:
        print(f"Error getting Edge voices: {e}")
        return []


async def text_to_speech_edge_async(text, voice_id, rate=0, volume=100):
    """Convert text to speech using Edge TTS (online neural voices)"""
    rate_percent = int((rate - 150) / 3)
    rate_str = f"{rate_percent:+d}%"
    vol_percent = int(volume - 50)
    vol_str = f"{vol_percent:+d}%"
    
    communicate = edge_tts.Communicate(text, voice_id, rate=rate_str, volume=vol_str)
    
    audio_bytes = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.write(chunk["data"])
    
    return audio_bytes.getvalue()


def text_to_speech_edge(text, voice_id, rate=150, volume=100, save_file=False):
    """Synchronous wrapper for Edge TTS using storage backend"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        audio_data = loop.run_until_complete(
            text_to_speech_edge_async(text, voice_id, rate, volume)
        )
        loop.close()
        
        if not audio_data:
            return {'status': 'error', 'message': 'No audio generated'}
        
        if save_file:
            filename = f"speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.mp3"
            if storage.save_file(filename, audio_data):
                return {
                    'status': 'success',
                    'message': 'Audio saved successfully',
                    'file': filename
                }
            else:
                return {'status': 'error', 'message': 'Failed to save audio'}
        else:
            filename = f"temp_{uuid.uuid4().hex[:8]}.mp3"
            if storage.save_file(filename, audio_data):
                return {
                    'status': 'success',
                    'message': 'Audio generated',
                    'temp_file': filename
                }
            else:
                return {'status': 'error', 'message': 'Failed to save temp audio'}
        
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# =============================================================================
# ROUTES
# =============================================================================

@tts_bp.route('/')
def index():
    """Render the TTS app UI"""
    # When embedded under /experiments/tts/, API calls need the prefix
    tts_base_url = '/experiments/tts'
    return render_template('app.html', base_url=tts_base_url, embed_mode=False)


@tts_bp.route('/api/voices', methods=['GET'])
def api_get_voices():
    """API endpoint to get all available Edge TTS voices"""
    try:
        voices = get_edge_voices()
        return jsonify({'status': 'success', 'voices': voices})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to fetch voices'}), 500


@tts_bp.route('/api/speak', methods=['POST'])
def api_speak():
    """API endpoint to speak text immediately"""
    data = request.get_json()
    
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid request body'}), 400
    
    text = sanitize_text(data.get('text'))
    if not text:
        return jsonify({'status': 'error', 'message': f'Text is required (max {MAX_TEXT_LENGTH} characters)'}), 400
    
    voice_id = validate_voice_id(data.get('voice_id'))
    if not voice_id:
        return jsonify({'status': 'error', 'message': 'Valid voice_id is required'}), 400
    
    rate = validate_numeric_param(data.get('rate'), 50, 300, 150)
    volume = validate_numeric_param(data.get('volume'), 0, 100, 100)
    
    result = text_to_speech_edge(text, voice_id, rate, volume, save_file=False)
    if result.get('temp_file'):
        result['audio_url'] = f"/experiments/tts/api/play/{result['temp_file']}"
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify({'status': 'error', 'message': 'Speech generation failed'}), 500


@tts_bp.route('/api/play/<filename>')
def api_play(filename):
    """API endpoint to serve audio for playback"""
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    if STORAGE_TYPE == 's3':
        url = storage.get_file_url(safe_filename)
        if url:
            return jsonify({'status': 'redirect', 'url': url})
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    if isinstance(storage, LocalStorage):
        filepath = storage.get_file_path(safe_filename)
        if filepath:
            return send_file(filepath, mimetype='audio/mpeg')
    
    file_data = storage.get_file(safe_filename)
    if file_data:
        return Response(file_data, mimetype='audio/mpeg')
    
    return jsonify({'status': 'error', 'message': 'File not found'}), 404


@tts_bp.route('/api/save', methods=['POST'])
def api_save():
    """API endpoint to save speech to file"""
    data = request.get_json()
    
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid request body'}), 400
    
    text = sanitize_text(data.get('text'))
    if not text:
        return jsonify({'status': 'error', 'message': f'Text is required (max {MAX_TEXT_LENGTH} characters)'}), 400
    
    voice_id = validate_voice_id(data.get('voice_id'))
    if not voice_id:
        return jsonify({'status': 'error', 'message': 'Valid voice_id is required'}), 400
    
    rate = validate_numeric_param(data.get('rate'), 50, 300, 150)
    volume = validate_numeric_param(data.get('volume'), 0, 100, 100)
    
    result = text_to_speech_edge(text, voice_id, rate, volume, save_file=True)
    
    if result['status'] == 'success':
        result['expires_in_seconds'] = FILE_MAX_AGE_SECONDS
        result['message'] = f"Audio saved. File will be auto-deleted in {FILE_MAX_AGE_SECONDS // 60} minutes."
        return jsonify(result)
    else:
        return jsonify({'status': 'error', 'message': 'Failed to save audio'}), 500


@tts_bp.route('/api/download/<filename>')
def api_download(filename):
    """API endpoint to download generated audio file"""
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    if STORAGE_TYPE == 's3':
        url = storage.get_file_url(safe_filename)
        if url:
            return jsonify({'status': 'redirect', 'url': url})
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    if isinstance(storage, LocalStorage):
        filepath = storage.get_file_path(safe_filename)
        if filepath:
            return send_file(filepath, as_attachment=True, download_name=safe_filename)
    
    file_data = storage.get_file(safe_filename)
    if file_data:
        return Response(
            file_data,
            mimetype='audio/mpeg',
            headers={'Content-Disposition': f'attachment; filename={safe_filename}'}
        )
    
    return jsonify({'status': 'error', 'message': 'File not found'}), 404


@tts_bp.route('/api/history', methods=['GET'])
def api_history():
    """API endpoint to get list of generated audio files"""
    try:
        files = storage.list_files(exclude_prefix='temp_')
        
        current_time = time.time()
        for file in files:
            age = current_time - file['created']
            remaining = max(0, FILE_MAX_AGE_SECONDS - age)
            file['expires_in_seconds'] = int(remaining)
            file['expires_in_minutes'] = int(remaining / 60)
        
        return jsonify({'status': 'success', 'files': files})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to fetch history'}), 500


@tts_bp.route('/api/delete/<filename>', methods=['DELETE'])
def api_delete(filename):
    """API endpoint to delete a generated audio file"""
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    if storage.delete_file(safe_filename):
        return jsonify({'status': 'success', 'message': 'File deleted'})
    else:
        return jsonify({'status': 'error', 'message': 'File not found or delete failed'}), 404
