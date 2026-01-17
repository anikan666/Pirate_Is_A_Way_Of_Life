"""
Pirate Lab - A Laboratory of AI Experiments
Main entry point that registers all experiment blueprints
"""

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS
from dotenv import load_dotenv
import os

from config import Config
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_app():
    """Application factory"""
    # Validate Configuration
    Config.validate()

    app = Flask(__name__, 
                template_folder=os.path.join(BASE_DIR, 'core', 'templates'),
                static_folder=os.path.join(BASE_DIR, 'core', 'static'))

    # Middleware to handle proxy headers (for Render/Heroku HTTPS)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Secret key for sessions
    app.secret_key = Config.SECRET_KEY
    
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
    from experiments.tts_pirate.routes import tts_bp, start_cleanup_task
    app.register_blueprint(tts_bp, url_prefix='/experiments/tts')
    
    # Start background tasks
    try:
        start_cleanup_task()
    except RuntimeError:
        # Ignore if thread already started (though in this new func it's fresh)
        pass
    
    # Register Daily Planner Blueprint
    from experiments.daily_planner.routes import daily_planner_bp
    app.register_blueprint(daily_planner_bp, url_prefix='/experiments/planner')

    # Register YouTube Summarizer Blueprint
    from experiments.youtube_summarizer.routes import youtube_bp
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
