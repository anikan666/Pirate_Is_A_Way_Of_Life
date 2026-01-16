"""
Authentication module for Daily Planner.
Handles OAuth2 flow with Google (login, callback, logout, check_auth).
"""
import os
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


def register_auth_routes(bp):
    """Register authentication routes on the given blueprint."""
    
    @bp.route('/login')
    def login():
        """Initiate OAuth2 login flow with Google."""
        if not os.path.exists(CLIENT_SECRETS_FILE):
            return "Error: credentials.json not found in project root. Please follow the instructions to download it from Google Cloud Console."

        redirect_uri = url_for('daily_planner.callback', _external=True)
        print(f"\n[DEBUG] OAuth Redirect URI: {redirect_uri}\nMake sure this EXACT URL is in your Google Cloud Console Authorized Redirect URIs.\n")

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
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
        
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=url_for('daily_planner.callback', _external=True)
        )
        
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
