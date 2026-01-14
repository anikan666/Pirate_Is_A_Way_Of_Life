"""
Why Should I Pay For ElevenLabs - Free Text-to-Speech
Supports Microsoft Edge TTS (300+ neural voices)

Security Features:
- Rate limiting (Flask-Limiter)
- CORS configuration (Flask-Cors)
- Input validation and sanitization

Storage Features:
- Local or S3 cloud storage
- Auto-deletion of files after 1 hour
"""

from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from dotenv import load_dotenv
import edge_tts
import asyncio
import os
import re
import uuid
import html
import io
import threading
import time
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Base URL for embedding (used when app is hosted on a subdomain/subpath)
BASE_URL = os.environ.get('BASE_URL', '').rstrip('/')

# Storage Configuration
STORAGE_TYPE = os.environ.get('STORAGE_TYPE', 'local').lower()
FILE_MAX_AGE_SECONDS = int(os.environ.get('FILE_MAX_AGE_SECONDS', 3600))  # 1 hour default

# Embedding Configuration
EMBED_ALLOWED = os.environ.get('EMBED_ALLOWED', 'true').lower() == 'true'
EMBED_PARENT_ORIGINS = os.environ.get('EMBED_PARENT_ORIGINS', '*')  # Allowed parent origins for iframe

# Import storage backend
from storage import get_storage_backend, LocalStorage
storage = get_storage_backend()

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# CORS Configuration
CORS(app, resources={
    r"/api/*": {
        "origins": os.environ.get('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(','),
        "methods": ["GET", "POST", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

# Rate Limiting Configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Input Validation Constants
MAX_TEXT_LENGTH = 5000
MAX_FILENAME_LENGTH = 100
ALLOWED_FILENAME_CHARS = re.compile(r'^[a-zA-Z0-9_\- ]+$')

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
            
            # Also clean up temp files (5 min max)
            if hasattr(storage, 'cleanup_temp_files'):
                storage.cleanup_temp_files(max_age_seconds=300)
                
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        # Run cleanup every 5 minutes
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
# TTS FUNCTIONALITY
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
    """
    Convert text to speech using Edge TTS (online)
    Returns audio bytes directly
    """
    rate_percent = int((rate - 150) / 3)
    rate_str = f"{rate_percent:+d}%"
    vol_percent = int(volume - 50)
    vol_str = f"{vol_percent:+d}%"
    
    communicate = edge_tts.Communicate(text, voice_id, rate=rate_str, volume=vol_str)
    
    # Collect audio bytes
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
            # Save as temp file
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
# API ENDPOINTS
# =============================================================================

@app.route('/')
@limiter.limit("60 per minute")
def index():
    """Render the main page"""
    return render_template('index.html', base_url=BASE_URL, embed_mode=False)


@app.route('/embed')
@limiter.limit("60 per minute")
def embed():
    """Render the embeddable widget version"""
    if not EMBED_ALLOWED:
        return jsonify({'status': 'error', 'message': 'Embedding is disabled'}), 403
    
    response = render_template('embed.html', base_url=BASE_URL, embed_mode=True)
    
    # Set headers for iframe embedding
    resp = app.make_response(response)
    if EMBED_PARENT_ORIGINS != '*':
        resp.headers['Content-Security-Policy'] = f"frame-ancestors {EMBED_PARENT_ORIGINS}"
    resp.headers['X-Frame-Options'] = 'ALLOWALL'
    return resp


@app.route('/embed-docs')
@limiter.limit("30 per minute")
def embed_docs():
    """Render the embedding documentation and example page"""
    return render_template('embed-example.html')


@app.route('/api/config', methods=['GET'])
@limiter.limit("30 per minute")
def api_config():
    """API endpoint to get frontend configuration"""
    return jsonify({
        'status': 'success',
        'base_url': BASE_URL,
        'storage_type': STORAGE_TYPE,
        'file_max_age_seconds': FILE_MAX_AGE_SECONDS,
        'embed_allowed': EMBED_ALLOWED
    })


@app.route('/api/voices', methods=['GET'])
@limiter.limit("30 per minute")
def api_get_voices():
    """API endpoint to get all available Edge TTS voices"""
    try:
        voices = get_edge_voices()
        return jsonify({'status': 'success', 'voices': voices})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to fetch voices'}), 500


@app.route('/api/speak', methods=['POST'])
@limiter.limit("20 per minute")
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
        result['audio_url'] = f"/api/play/{result['temp_file']}"
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify({'status': 'error', 'message': 'Speech generation failed'}), 500


@app.route('/api/play/<filename>')
@limiter.limit("60 per minute")
def api_play(filename):
    """API endpoint to serve audio for playback"""
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    # For S3, redirect to presigned URL
    if STORAGE_TYPE == 's3':
        url = storage.get_file_url(safe_filename)
        if url:
            return jsonify({'status': 'redirect', 'url': url})
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    # For local storage, serve the file directly
    if isinstance(storage, LocalStorage):
        filepath = storage.get_file_path(safe_filename)
        if filepath:
            return send_file(filepath, mimetype='audio/mpeg')
    
    # Fallback: get file bytes and serve
    file_data = storage.get_file(safe_filename)
    if file_data:
        return Response(file_data, mimetype='audio/mpeg')
    
    return jsonify({'status': 'error', 'message': 'File not found'}), 404


@app.route('/api/save', methods=['POST'])
@limiter.limit("10 per minute")
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
        # Add note about auto-deletion
        result['expires_in_seconds'] = FILE_MAX_AGE_SECONDS
        result['message'] = f"Audio saved. File will be auto-deleted in {FILE_MAX_AGE_SECONDS // 60} minutes."
        return jsonify(result)
    else:
        return jsonify({'status': 'error', 'message': 'Failed to save audio'}), 500


@app.route('/api/download/<filename>')
@limiter.limit("30 per minute")
def api_download(filename):
    """API endpoint to download generated audio file"""
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    # For S3, redirect to presigned URL
    if STORAGE_TYPE == 's3':
        url = storage.get_file_url(safe_filename)
        if url:
            return jsonify({'status': 'redirect', 'url': url})
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    # For local storage
    if isinstance(storage, LocalStorage):
        filepath = storage.get_file_path(safe_filename)
        if filepath:
            return send_file(filepath, as_attachment=True, download_name=safe_filename)
    
    # Fallback
    file_data = storage.get_file(safe_filename)
    if file_data:
        return Response(
            file_data,
            mimetype='audio/mpeg',
            headers={'Content-Disposition': f'attachment; filename={safe_filename}'}
        )
    
    return jsonify({'status': 'error', 'message': 'File not found'}), 404


@app.route('/api/history', methods=['GET'])
@limiter.limit("30 per minute")
def api_history():
    """API endpoint to get list of generated audio files"""
    try:
        files = storage.list_files(exclude_prefix='temp_')
        
        # Add time remaining info
        current_time = time.time()
        for file in files:
            age = current_time - file['created']
            remaining = max(0, FILE_MAX_AGE_SECONDS - age)
            file['expires_in_seconds'] = int(remaining)
            file['expires_in_minutes'] = int(remaining / 60)
        
        return jsonify({'status': 'success', 'files': files})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to fetch history'}), 500


@app.route('/api/delete/<filename>', methods=['DELETE'])
@limiter.limit("20 per minute")
def api_delete(filename):
    """API endpoint to delete a generated audio file"""
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    if storage.delete_file(safe_filename):
        return jsonify({'status': 'success', 'message': 'File deleted'})
    else:
        return jsonify({'status': 'error', 'message': 'File not found or delete failed'}), 404


@app.route('/api/rename/<filename>', methods=['POST'])
@limiter.limit("20 per minute")
def api_rename_file(filename):
    """API endpoint to rename an audio file"""
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    if not storage.file_exists(safe_filename):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid request body'}), 400
        
        new_name = data.get('new_name', '').strip()
        
        if not new_name:
            return jsonify({'status': 'error', 'message': 'New name is required'}), 400
        
        if len(new_name) > MAX_FILENAME_LENGTH:
            return jsonify({'status': 'error', 'message': f'Filename too long (max {MAX_FILENAME_LENGTH} chars)'}), 400
        
        ext = os.path.splitext(safe_filename)[1]
        safe_new_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_new_name:
            return jsonify({'status': 'error', 'message': 'Invalid filename characters'}), 400
        
        new_filename = safe_new_name + ext
        
        if storage.file_exists(new_filename) and new_filename != safe_filename:
            return jsonify({'status': 'error', 'message': 'A file with that name already exists'}), 400
        
        if storage.rename_file(safe_filename, new_filename):
            return jsonify({'status': 'success', 'message': 'File renamed', 'new_filename': new_filename})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to rename file'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to rename file'}), 500


@app.route('/api/storage-info', methods=['GET'])
@limiter.limit("30 per minute")
def api_storage_info():
    """API endpoint to get storage configuration info"""
    return jsonify({
        'status': 'success',
        'storage_type': STORAGE_TYPE,
        'file_max_age_seconds': FILE_MAX_AGE_SECONDS,
        'file_max_age_minutes': FILE_MAX_AGE_SECONDS // 60,
        'auto_delete_enabled': True
    })


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'status': 'error',
        'message': 'Rate limit exceeded. Please slow down.',
        'retry_after': e.description
    }), 429


@app.errorhandler(400)
def bad_request_handler(e):
    return jsonify({'status': 'error', 'message': 'Bad request'}), 400


@app.errorhandler(500)
def internal_error_handler(e):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎙️ Why Should I Pay For ElevenLabs - Free TTS")
    print("="*60)
    print(f"\n📍 Open http://localhost:5000 in your browser")
    print(f"🌐 Online voices: Microsoft Edge TTS (300+ neural voices)")
    print(f"🔒 Security: Rate limiting & CORS enabled")
    print(f"💾 Storage: {STORAGE_TYPE.upper()}")
    print(f"⏰ Auto-delete: Files expire after {FILE_MAX_AGE_SECONDS // 60} minutes")
    print("\n" + "="*60 + "\n")
    
    app.run(debug=True, port=5000)
