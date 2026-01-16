"""
Configuration module for Daily Planner.
Stores all constants and configuration settings.
"""
import os

# Base directory setup
# .../daily_planner/config.py -> .../daily_planner -> .../experiments -> .../Text to speech
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Auth
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, 'credentials.json')
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly', 
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/calendar.events',
    'openid'
]

# Gmail
GMAIL_LABEL = 'Tasks to be tracked'
MAX_RESULTS = 20
EMAIL_BODY_MAX_LENGTH = 2000

# Calendar
DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'Asia/Kolkata')
DEFAULT_EVENT_DURATION_MINUTES = 60
