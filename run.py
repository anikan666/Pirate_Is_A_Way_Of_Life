"""
Pirate Lab - A Laboratory of AI Experiments
Main entry point that registers all experiment blueprints
"""

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_app():
    """Application factory"""
    app = Flask(__name__, 
                template_folder=os.path.join(BASE_DIR, 'core', 'templates'),
                static_folder=os.path.join(BASE_DIR, 'core', 'static'))
    
    # Secret key for sessions
    app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_super_secret_pirate')
    
    # CORS Configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": os.environ.get('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(','),
            "methods": ["GET", "POST", "DELETE"],
            "allow_headers": ["Content-Type"]
        }
    })
    
    # Register Core Routes (the Launchpad)
    from core.routes import core_bp
    app.register_blueprint(core_bp)
    
    # Register Experiment Blueprints
    from experiments.tts_pirate.routes import tts_bp
    app.register_blueprint(tts_bp, url_prefix='/experiments/tts')
    
    # Register Daily Planner Blueprint
    from experiments.daily_planner.routes import daily_planner_bp
    app.register_blueprint(daily_planner_bp, url_prefix='/experiments/planner')

    # Register YouTube Summarizer Blueprint
    from experiments.youtube_summarizer.app import youtube_bp
    app.register_blueprint(youtube_bp, url_prefix='/experiments/youtube-summarizer')
    
    return app


if __name__ == '__main__':
    app = create_app()
    
    print("\n" + "="*60)
    print("🏴‍☠️  PIRATE LAB - AI Experiments Laboratory")
    print("="*60)
    print(f"\n📍 Open http://localhost:5000 in your browser")
    print(f"🧪 Available Experiments:")
    print(f"   • TTS Pirate - /experiments/tts/")
    print("\n" + "="*60 + "\n")
    
    app.run(debug=True, port=5000)
