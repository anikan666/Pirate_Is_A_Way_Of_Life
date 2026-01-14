"""
Why Should I Pay For ElevenLabs - Free Text-to-Speech
Supports both offline (pyttsx3) and online (Edge TTS) speech synthesis
"""

from flask import Flask, render_template, request, jsonify, send_file
import pyttsx3
import edge_tts
import asyncio
import os
import uuid
import threading
from datetime import datetime

app = Flask(__name__)

# Directory to store generated audio files
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio_output')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Thread lock for pyttsx3 (not thread-safe)
tts_lock = threading.Lock()

# Cache for Edge TTS voices
edge_voices_cache = None


def get_offline_voices():
    """Get list of available offline voices (pyttsx3/SAPI)"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    voice_list = []
    for voice in voices:
        voice_list.append({
            'id': voice.id,
            'name': voice.name,
            'type': 'offline',
            'languages': getattr(voice, 'languages', []),
            'gender': getattr(voice, 'gender', 'unknown')
        })
    engine.stop()
    return voice_list


async def get_edge_voices_async():
    """Get list of available Edge TTS voices"""
    voices = await edge_tts.list_voices()
    voice_list = []
    for voice in voices:
        # Only include English voices for simplicity, but include all
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


def text_to_speech_offline(text, voice_id=None, rate=150, volume=1.0, save_file=False):
    """
    Convert text to speech using pyttsx3 (offline)
    """
    with tts_lock:
        engine = pyttsx3.init()
        
        if voice_id:
            engine.setProperty('voice', voice_id)
        
        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)
        
        result = {'status': 'success', 'message': 'Speech generated successfully'}
        
        if save_file:
            filename = f"speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.mp3"
            filepath = os.path.join(AUDIO_DIR, filename)
            
            try:
                engine.save_to_file(text, filepath)
                engine.runAndWait()
                result['file'] = filename
                result['filepath'] = filepath
            except Exception as e:
                result = {'status': 'error', 'message': str(e)}
        else:
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                result = {'status': 'error', 'message': str(e)}
        
        engine.stop()
        return result


async def text_to_speech_edge_async(text, voice_id, rate=0, volume=100, filepath=None):
    """
    Convert text to speech using Edge TTS (online)
    Rate: -50 to +50 (percentage change)
    Volume: -50 to +50 (percentage change)
    """
    # Convert rate from wpm to percentage
    # Default is ~180 wpm, so adjust accordingly
    rate_percent = int((rate - 150) / 3)  # Maps 50-300 to roughly -33% to +50%
    rate_str = f"{rate_percent:+d}%"
    
    # Convert volume from 0-100 to -50 to +50
    vol_percent = int(volume - 50)
    vol_str = f"{vol_percent:+d}%"
    
    communicate = edge_tts.Communicate(text, voice_id, rate=rate_str, volume=vol_str)
    
    if filepath:
        await communicate.save(filepath)
        return {'status': 'success', 'message': 'Audio saved successfully'}
    else:
        # For playback, we need to save temporarily and then play
        # Edge TTS doesn't support direct playback
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


@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


@app.route('/api/voices', methods=['GET'])
def api_get_voices():
    """API endpoint to get all available voices (offline + Edge TTS)"""
    try:
        all_voices = []
        
        # Get offline voices
        try:
            offline_voices = get_offline_voices()
            all_voices.extend(offline_voices)
        except Exception as e:
            print(f"Error getting offline voices: {e}")
        
        # Get Edge TTS voices
        try:
            edge_voices = get_edge_voices()
            all_voices.extend(edge_voices)
        except Exception as e:
            print(f"Error getting Edge voices: {e}")
        
        return jsonify({'status': 'success', 'voices': all_voices})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/speak', methods=['POST'])
def api_speak():
    """API endpoint to speak text immediately"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400
    
    text = data['text']
    voice_id = data.get('voice_id')
    voice_type = data.get('voice_type', 'offline')
    rate = int(data.get('rate', 150))
    volume = float(data.get('volume', 1.0))
    
    # Validate parameters
    rate = max(50, min(300, rate))
    
    if voice_type == 'edge':
        # Edge TTS - save to temp file and return path for browser playback
        volume_percent = int(volume * 100)
        result = text_to_speech_edge(text, voice_id, rate, volume_percent, save_file=False)
        if result.get('temp_file'):
            result['audio_url'] = f"/api/play/{os.path.basename(result['temp_file'])}"
    else:
        # Offline TTS - speaks through system speakers
        volume = max(0.0, min(1.0, volume))
        result = text_to_speech_offline(text, voice_id, rate, volume, save_file=False)
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify(result), 500


@app.route('/api/play/<filename>')
def api_play(filename):
    """API endpoint to serve audio for playback"""
    filepath = os.path.join(AUDIO_DIR, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='audio/mpeg')
    else:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404


@app.route('/api/save', methods=['POST'])
def api_save():
    """API endpoint to save speech to file"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400
    
    text = data['text']
    voice_id = data.get('voice_id')
    voice_type = data.get('voice_type', 'offline')
    rate = int(data.get('rate', 150))
    volume = float(data.get('volume', 1.0))
    
    # Validate parameters
    rate = max(50, min(300, rate))
    
    if voice_type == 'edge':
        volume_percent = int(volume * 100)
        result = text_to_speech_edge(text, voice_id, rate, volume_percent, save_file=True)
    else:
        volume = max(0.0, min(1.0, volume))
        result = text_to_speech_offline(text, voice_id, rate, volume, save_file=True)
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify(result), 500


@app.route('/api/download/<filename>')
def api_download(filename):
    """API endpoint to download generated audio file"""
    filepath = os.path.join(AUDIO_DIR, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    else:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404


@app.route('/api/history', methods=['GET'])
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
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/delete/<filename>', methods=['DELETE'])
def api_delete(filename):
    """API endpoint to delete a generated audio file"""
    filepath = os.path.join(AUDIO_DIR, filename)
    
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return jsonify({'status': 'success', 'message': 'File deleted'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404


@app.route('/api/rename/<filename>', methods=['POST'])
def api_rename_file(filename):
    """API endpoint to rename an audio file"""
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        try:
            data = request.get_json()
            new_name = data.get('new_name', '').strip()
            
            if not new_name:
                return jsonify({'status': 'error', 'message': 'New name is required'}), 400
            
            # Sanitize filename - keep extension
            ext = os.path.splitext(filename)[1]
            # Remove invalid characters
            safe_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_name:
                return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
            
            new_filename = safe_name + ext
            new_filepath = os.path.join(AUDIO_DIR, new_filename)
            
            # Avoid overwriting existing files
            if os.path.exists(new_filepath) and new_filepath != filepath:
                return jsonify({'status': 'error', 'message': 'A file with that name already exists'}), 400
            
            os.rename(filepath, new_filepath)
            return jsonify({'status': 'success', 'message': 'File renamed', 'new_filename': new_filename})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404


# Cleanup temp files periodically
def cleanup_temp_files():
    """Remove temporary audio files older than 5 minutes"""
    try:
        import time
        current_time = time.time()
        for filename in os.listdir(AUDIO_DIR):
            if filename.startswith('temp_'):
                filepath = os.path.join(AUDIO_DIR, filename)
                if current_time - os.path.getctime(filepath) > 300:  # 5 minutes
                    os.remove(filepath)
    except Exception as e:
        print(f"Error cleaning up temp files: {e}")


if __name__ == '__main__':
    print("\n" + "="*55)
    print("🎙️ Why Should I Pay For ElevenLabs - Free TTS")
    print("="*55)
    print("\n📍 Open http://localhost:5000 in your browser")
    print("🔊 Offline voices: Windows SAPI")
    print("🌐 Online voices: Microsoft Edge TTS (300+ voices)")
    print("💾 Audio files saved to:", AUDIO_DIR)
    print("\n" + "="*55 + "\n")
    
    # Initial cleanup
    cleanup_temp_files()
    
    app.run(debug=True, port=5000)
