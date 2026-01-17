"""
Authentication module for Daily Planner.
Handles OAuth2 flow with Google (login, callback, logout, check_auth).
"""
import os
import json
from flask import redirect, url_for, session, request
from google_auth_oauthlib.flow import Flow

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, 'credentials.json')
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly', 
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/calendar.events',
    'openid'
]

# Allow OAuth over HTTP for local testing
# Only set this in development environments
if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


def get_flow(redirect_uri=None, state=None):
    """
    Create a Flow instance from either:
    1. GOOGLE_CREDENTIALS_JSON environment variable (Production)
    2. credentials.json file (Development)
    """
    # Option 1: Env Var (Production)
    if os.environ.get('GOOGLE_CREDENTIALS_JSON'):
        try:
            client_config = json.loads(os.environ['GOOGLE_CREDENTIALS_JSON'])
            return Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri,
                state=state
            )
        except json.JSONDecodeError:
             raise ValueError("GOOGLE_CREDENTIALS_JSON env var contains invalid JSON.")
    
    # Option 2: File (Development)
    if os.path.exists(CLIENT_SECRETS_FILE):
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            state=state
        )
    
    raise FileNotFoundError("Neither GOOGLE_CREDENTIALS_JSON env var nor credentials.json file found.")


def register_auth_routes(bp):
    """Register authentication routes on the given blueprint."""
    
    @bp.route('/login')
    def login():
        """Initiate OAuth2 login flow with Google."""
        redirect_uri = url_for('daily_planner.callback', _external=True)
        
        # Debug info for redirect URI mismatch issues
        print(f"\n[DEBUG] OAuth Redirect URI: {redirect_uri}\nMake sure this EXACT URL is in your Google Cloud Console Authorized Redirect URIs.\n")

        try:
            flow = get_flow(redirect_uri=redirect_uri)
        except (FileNotFoundError, ValueError) as e:
            return f"Authentication Error: {str(e)}", 500

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        session['state'] = state
        return redirect(authorization_url)

    @bp.route('/callback')
    def callback():
        """Handle OAuth2 callback from Google."""
        state = session.get('state')
        
        try:
            flow = get_flow(
                redirect_uri=url_for('daily_planner.callback', _external=True),
                state=state
            )
        except (FileNotFoundError, ValueError) as e:
            return f"Authentication Error: {str(e)}", 500
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        return "<script>window.close();</script>"

    @bp.route('/logout')
    def logout():
        """Clear credentials and redirect to index."""
        session.pop('credentials', None)
        return redirect(url_for('daily_planner.index'))

    @bp.route('/check_auth')
    def check_auth():
        """Return authentication status as JSON."""
        return {'authenticated': 'credentials' in session}
