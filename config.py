import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """Base configuration class."""
    # Core Flask Config
    SECRET_KEY = os.environ.get('SECRET_KEY')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

    # LLM / AI Config
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'anthropic')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'claude-haiku-4-5-20251001')

    # Common Settings
    TIMEZONE = os.environ.get('TIMEZONE', 'UTC')
    BASE_URL = os.environ.get('BASE_URL', '').rstrip('/')
    STORAGE_TYPE = os.environ.get('STORAGE_TYPE', 'local').lower()
    FILE_MAX_AGE_SECONDS = int(os.environ.get('FILE_MAX_AGE_SECONDS', 3600))

    @classmethod
    def validate(cls):
        """Validate critical configuration."""
        if cls.FLASK_ENV == 'production':
            if not cls.SECRET_KEY:
                raise ValueError("SECRET_KEY must be set in production environment.")
        
        # Fallback for development
        if not cls.SECRET_KEY and cls.FLASK_ENV != 'production':
            logging.warning("No SECRET_KEY set. Using default development key.")
            cls.SECRET_KEY = 'dev-key-please-change-in-prod'
