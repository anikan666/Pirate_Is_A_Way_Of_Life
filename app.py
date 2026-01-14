"""
Why Should I Pay For ElevenLabs - Free Text-to-Speech
Supports Microsoft Edge TTS (300+ neural voices)

Security Features:
- Rate limiting (Flask-Limiter)
- CORS configuration (Flask-Cors)
- Input validation and sanitization
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import edge_tts
import asyncio
import os
import re
import uuid
import html
from datetime import datetime

app = Flask(__name__)

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# CORS Configuration - Restrict to specific origins in production
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
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
MAX_TEXT_LENGTH = 5000  # Maximum characters for TTS
MAX_FILENAME_LENGTH = 100  # Maximum filename length
ALLOWED_FILENAME_CHARS = re.compile(r'^[a-zA-Z0-9_\- ]+$')

# =============================================================================
# INPUT VALIDATION HELPERS
# =============================================================================

def sanitize_text(text):
    """Sanitize input text for TTS processing"""
    if not text or not isinstance(text, str):
        return None
    
    # Strip whitespace
    text = text.strip()
    
    # Check length
    if len(text) == 0 or len(text) > MAX_TEXT_LENGTH:
        return None
    
    # Escape HTML entities to prevent injection
    text = html.escape(text)
    
    return text


def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal and injection"""
    if not filename or not isinstance(filename, str):
        return None
    
    # Remove any path components (prevent directory traversal)
    filename = os.path.basename(filename)
    
    # Check length
    if len(filename) == 0 or len(filename) > MAX_FILENAME_LENGTH:
        return None
    
    # Only allow safe characters
    name, ext = os.path.splitext(filename)
    if ext.lower() not in ['.mp3', '.wav']:
        return None
    
    # Sanitize the name part
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_name:
        return None
    
    return safe_name + ext


def validate_voice_id(voice_id):
    """Validate voice ID format"""
    if not voice_id or not isinstance(voice_id, str):
        return None
    
    # Edge TTS voice IDs follow pattern: xx-XX-NameNeural
    # Allow alphanumeric, hyphens, and underscores
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

# Directory to store generated audio files
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio_output')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Cache for Edge TTS voices
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


async def text_to_speech_edge_async(text, voice_id, rate=0, volume=100, filepath=None):
    """
    Convert text to speech using Edge TTS (online)
    Rate: -50 to +50 (percentage change)
    Volume: -50 to +50 (percentage change)
    """
    # Convert rate from wpm to percentage
    rate_percent = int((rate - 150) / 3)
    rate_str = f"{rate_percent:+d}%"
    
    # Convert volume from 0-100 to -50 to +50
    vol_percent = int(volume - 50)
    vol_str = f"{vol_percent:+d}%"
    
    communicate = edge_tts.Communicate(text, voice_id, rate=rate_str, volume=vol_str)
    
    if filepath:
        await communicate.save(filepath)
        return {'status': 'success', 'message': 'Audio saved successfully'}
    else:
        temp_file = os.path.join(AUDIO_DIR, f"temp_{uuid.uuid4().hex[:8]}.mp3")
        await communicate.save(temp_file)
        return {'status': 'success', 'message': 'Audio generated', 'temp_file': temp_file}


def text_to_speech_edge(text, voice_id, rate=150, volume=100, save_file=False):
    """Synchronous wrapper for Edge TTS"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        filename = None
        filepath = None
        
        if save_file:
            filename = f"speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.mp3"
            filepath = os.path.join(AUDIO_DIR, filename)
        
        result = loop.run_until_complete(
            text_to_speech_edge_async(text, voice_id, rate, volume, filepath)
        )
        loop.close()
        
        if save_file and result['status'] == 'success':
            result['file'] = filename
            result['filepath'] = filepath
        
        return result
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/')
@limiter.limit("60 per minute")
def index():
    """Render the main page"""
    return render_template('index.html')


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
    
    # Validate and sanitize text
    text = sanitize_text(data.get('text'))
    if not text:
        return jsonify({'status': 'error', 'message': f'Text is required (max {MAX_TEXT_LENGTH} characters)'}), 400
    
    # Validate voice ID
    voice_id = validate_voice_id(data.get('voice_id'))
    if not voice_id:
        return jsonify({'status': 'error', 'message': 'Valid voice_id is required'}), 400
    
    # Validate numeric parameters
    rate = validate_numeric_param(data.get('rate'), 50, 300, 150)
    volume = validate_numeric_param(data.get('volume'), 0, 100, 100)
    
    # Generate speech
    result = text_to_speech_edge(text, voice_id, rate, volume, save_file=False)
    if result.get('temp_file'):
        result['audio_url'] = f"/api/play/{os.path.basename(result['temp_file'])}"
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify({'status': 'error', 'message': 'Speech generation failed'}), 500


@app.route('/api/play/<filename>')
@limiter.limit("60 per minute")
def api_play(filename):
    """API endpoint to serve audio for playback"""
    # Sanitize filename to prevent path traversal
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    filepath = os.path.join(AUDIO_DIR, safe_filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='audio/mpeg')
    else:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404


@app.route('/api/save', methods=['POST'])
@limiter.limit("10 per minute")
def api_save():
    """API endpoint to save speech to file"""
    data = request.get_json()
    
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid request body'}), 400
    
    # Validate and sanitize text
    text = sanitize_text(data.get('text'))
    if not text:
        return jsonify({'status': 'error', 'message': f'Text is required (max {MAX_TEXT_LENGTH} characters)'}), 400
    
    # Validate voice ID
    voice_id = validate_voice_id(data.get('voice_id'))
    if not voice_id:
        return jsonify({'status': 'error', 'message': 'Valid voice_id is required'}), 400
    
    # Validate numeric parameters
    rate = validate_numeric_param(data.get('rate'), 50, 300, 150)
    volume = validate_numeric_param(data.get('volume'), 0, 100, 100)
    
    # Generate and save speech
    result = text_to_speech_edge(text, voice_id, rate, volume, save_file=True)
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify({'status': 'error', 'message': 'Failed to save audio'}), 500


@app.route('/api/download/<filename>')
@limiter.limit("30 per minute")
def api_download(filename):
    """API endpoint to download generated audio file"""
    # Sanitize filename to prevent path traversal
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    filepath = os.path.join(AUDIO_DIR, safe_filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=safe_filename)
    else:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404


@app.route('/api/history', methods=['GET'])
@limiter.limit("30 per minute")
def api_history():
    """API endpoint to get list of generated audio files"""
    try:
        files = []
        for filename in os.listdir(AUDIO_DIR):
            # Skip temp files
            if filename.startswith('temp_'):
                continue
            if filename.endswith(('.mp3', '.wav')):
                filepath = os.path.join(AUDIO_DIR, filename)
                files.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'created': os.path.getctime(filepath)
                })
        # Sort by creation time, newest first
        files.sort(key=lambda x: x['created'], reverse=True)
        return jsonify({'status': 'success', 'files': files})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to fetch history'}), 500


@app.route('/api/delete/<filename>', methods=['DELETE'])
@limiter.limit("20 per minute")
def api_delete(filename):
    """API endpoint to delete a generated audio file"""
    # Sanitize filename to prevent path traversal
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    filepath = os.path.join(AUDIO_DIR, safe_filename)
    
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return jsonify({'status': 'success', 'message': 'File deleted'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': 'Failed to delete file'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404


@app.route('/api/rename/<filename>', methods=['POST'])
@limiter.limit("20 per minute")
def api_rename_file(filename):
    """API endpoint to rename an audio file"""
    # Sanitize original filename
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    filepath = os.path.join(AUDIO_DIR, safe_filename)
    
    if not os.path.exists(filepath):
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
        
        # Sanitize new filename
        ext = os.path.splitext(safe_filename)[1]
        safe_new_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_new_name:
            return jsonify({'status': 'error', 'message': 'Invalid filename characters'}), 400
        
        new_filename = safe_new_name + ext
        new_filepath = os.path.join(AUDIO_DIR, new_filename)
        
        # Avoid overwriting existing files
        if os.path.exists(new_filepath) and new_filepath != filepath:
            return jsonify({'status': 'error', 'message': 'A file with that name already exists'}), 400
        
        os.rename(filepath, new_filepath)
        return jsonify({'status': 'success', 'message': 'File renamed', 'new_filename': new_filename})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to rename file'}), 500


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors"""
    return jsonify({
        'status': 'error',
        'message': 'Rate limit exceeded. Please slow down.',
        'retry_after': e.description
    }), 429


@app.errorhandler(400)
def bad_request_handler(e):
    """Handle bad request errors"""
    return jsonify({'status': 'error', 'message': 'Bad request'}), 400


@app.errorhandler(500)
def internal_error_handler(e):
    """Handle internal server errors"""
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def cleanup_temp_files():
    """Remove temporary audio files older than 5 minutes"""
    try:
        import time
        current_time = time.time()
        for filename in os.listdir(AUDIO_DIR):
            if filename.startswith('temp_'):
                filepath = os.path.join(AUDIO_DIR, filename)
                if current_time - os.path.getctime(filepath) > 300:
                    os.remove(filepath)
    except Exception as e:
        print(f"Error cleaning up temp files: {e}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*55)
    print("🎙️ Why Should I Pay For ElevenLabs - Free TTS")
    print("="*55)
    print("\n📍 Open http://localhost:5000 in your browser")
    print("🌐 Online voices: Microsoft Edge TTS (300+ neural voices)")
    print("🔒 Security: Rate limiting & CORS enabled")
    print("💾 Audio files saved to:", AUDIO_DIR)
    print("\n" + "="*55 + "\n")
    
    # Initial cleanup
    cleanup_temp_files()
    
    app.run(debug=True, port=5000)
