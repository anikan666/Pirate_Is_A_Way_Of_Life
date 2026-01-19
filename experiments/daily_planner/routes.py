import os
import logging
import datetime
import json
from flask import Blueprint, render_template, redirect, url_for, session, request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

daily_planner_bp = Blueprint('daily_planner', __name__, template_folder='templates')
logger = logging.getLogger(__name__)

# Register auth routes from auth module
from experiments.daily_planner.auth import register_auth_routes
from experiments.daily_planner.gmail_service import (
    get_gmail_service, 
    fetch_emails_from_label, 
    extract_sender_name
)
from experiments.daily_planner.ai_service import generate_plan
from experiments.daily_planner.calendar_service import (
    get_calendar_service,
    sync_tasks_to_calendar
)
register_auth_routes(daily_planner_bp)

# Configuration
from experiments.daily_planner.config import (
    CLIENT_SECRETS_FILE, 
    SCOPES, 
    EMAIL_BODY_MAX_LENGTH
)
from config import Config

# Debug Environment Loading
provider = Config.LLM_PROVIDER
logger.debug(f"LLM_PROVIDER is currently: '{provider}'")
if provider == 'gemini':
    key_status = "Set" if Config.GEMINI_API_KEY else "Missing"
    logger.debug(f"GEMINI_API_KEY is: {key_status}")
elif provider == 'anthropic':
    key_status = "Set" if Config.ANTHROPIC_API_KEY else "Missing"
    logger.debug(f"ANTHROPIC_API_KEY is: {key_status}")

@daily_planner_bp.route('/')
def index():
    # Always clear credentials when index loads to force fresh login
    # This ensures each modal open requires authentication
    session.pop('credentials', None)
    session.pop('state', None)
    return render_template('planner_index.html')

@daily_planner_bp.route('/dashboard')
def dashboard():
    if 'credentials' not in session:
        return redirect(url_for('daily_planner.login'))
    
    try:
        # Use gmail_service module for email fetching
        service = get_gmail_service(session['credentials'])
        email_data = fetch_emails_from_label(service)

        # DEBUG: Show user what the API is actually fetching
        logger.debug("--- GMAIL API DEBUG RESPONSE (Full Context) ---")
        if email_data:
            logger.debug(f"Fetched {len(email_data)} emails from 'Tasks to be tracked'. First entry body length: {len(email_data[0]['snippet'])}")
            # Print first 500 chars of first email body
            logger.debug(f"Body Preview:\n{email_data[0]['snippet'][:500]}...")
        else:
            logger.debug("Fetched 0 emails from 'Tasks to be tracked'.")
        logger.debug("-----------------------------------------------")

        # SHORT CIRCUIT: If no emails, don't ask AI to hallucinate
        if not email_data:
            return render_template('planner_dashboard.html', 
                             date=datetime.date.today().strftime("%A, %B %d"),
                             summary="You are all caught up! No new emails in the last 24 hours.",
                             tasks=[],
                             schedule=[],
                             stats={'analyzed': 0, 'actionable': 0, 'newsletters': 0},
                             emails=[])

        # 2. AI Planning Logic
        # --------------------
        
        # Prepare the prompt
        # We pass the full body now, up to 2000 chars per email to avoid hitting token limits too fast
        email_text = "\n\n".join([f"EMAIL #{i+1}:\n- From: {e['sender']}\n- Subject: {e['subject']}\n- BODY:\n{e['snippet'][:EMAIL_BODY_MAX_LENGTH]}" for i, e in enumerate(email_data)])
        prompt = f"""
You are an elite Executive Assistant for **Anish Sood**. 
I will give you emails from my "Tasks to be tracked" folder.

INPUT EMAILS:
{email_text}

Your Goal: Extract ACTIONABLE TASKS and correctly identify WHO needs to take action.

CRITICAL LOGIC FOR IDENTIFYING THE ASSIGNEE:

**READ CAREFULLY**: The SENDER of an email is NOT always the person who needs to act!
- If Jennifer SENDS an email ASKING Radhika for something, then Radhika is the assignee (she needs to respond)
- If someone SENDS Anish a request, then Anish is the assignee  
- If someone SENDS a status update, then it is FYI (no action needed)

Ask yourself: "Who is being ASKED to do something in this email?"

RULES:

1. **action_type**:
   - "Do": Anish is being asked to do something
   - "Follow-up": Someone else was asked to do something, Anish should track it
   - "FYI": Status updates, confirmations, newsletters (no action needed)

2. **assignee**: The person who needs to PERFORM the action
   - Look at who is being REQUESTED to do something
   - If the email says "please send X" or "kindly share Y" - the recipient of that request is the assignee
   - Example: Jennifer asks Radhika for an estimate, then assignee = "Radhika"
   - Example: Client asks Anish to review, then assignee = "You"

3. **title**: Clear, actionable. Format:
   - "Follow up: [Assignee] to [action]"
   - Example: "Follow up: Radhika to send creative estimate"

4. **people**: Key stakeholders mentioned (for context)

5. **timeline_context**: Deadlines from email body, or "No deadline"

6. **urgency**: "Critical", "High", "Normal", or "Low"

7. **source_email_id**: The EMAIL # (1, 2, 3...)

Output ONLY valid JSON:

{{
    "summary": "X tasks for you, Y follow-ups, Z FYI.",
    "tasks": [
        {{ 
            "title": "Follow up: Radhika to send creative estimate", 
            "description": "Jennifer requested collateral estimate from Radhika",
            "action_type": "Follow-up",
            "assignee": "Radhika",
            "people": ["Jennifer", "Radhika"], 
            "timeline_context": "Next week",
            "urgency": "Normal",
            "source_email_id": 1 
        }}
    ]
}}
"""

        # Use ai_service module for LLM generation
        plan_data = generate_plan(prompt)

        # 3. Final Data Preparation (Real or Mock)
        # 3. Final Data Preparation (Real or Mock)
        # Check if generation failed (None or has 'error' key)
        # Check if generation failed (None or has 'error' key)
        if not plan_data or plan_data.get('error'):
            # NO FALLBACK - Show error explicitly as requested
            error_msg = plan_data.get('details', 'Unknown Error') if plan_data else "AI unavailable"
            
            if "ANTHROPIC_API_KEY" in error_msg:
                 error_msg = "Missing ANTHROPIC_API_KEY in Render Environment Variables"
            
            summary = f"⚠️ AI Generation Failed: {error_msg}"
            tasks = []
            schedule = []
        else:
            summary = plan_data.get('summary', 'No summary generated.')
            tasks = plan_data.get('tasks', [])
            for t in tasks: 
                t['source'] = 'AI Extraction'
                # Ensure source_email_id exists
                if 'source_email_id' not in t:
                    t['source_email_id'] = None
            schedule = plan_data.get('schedule', [])

        # --- GRID LAYOUT: 8 Hours × 4 Quarter-slots ---
        # Each hour row has 4 columns for :00, :15, :30, :45
        # This fits on one screen without scrolling while allowing 15-min granularity
        schedule_by_hour = []
        for hour in range(9, 17):  # 9 AM to 4 PM
            if hour < 12:
                hour_label = f"{hour}:00 AM"
            elif hour == 12:
                hour_label = "12:00 PM"
            else:
                hour_label = f"{hour - 12}:00 PM"
            
            quarter_slots = []
            for minute in [0, 15, 30, 45]:
                if hour < 12:
                    time_str = f"{hour}:{minute:02d} AM"
                elif hour == 12:
                    time_str = f"12:{minute:02d} PM"
                else:
                    time_str = f"{hour - 12}:{minute:02d} PM"
                
                # Check if this slot has a scheduled item
                slot_data = {
                    'time': time_str,
                    'minute': minute,
                    'type': 'empty'
                }
                # Look for matching scheduled item
                for item in schedule:
                    if item.get('time', '').strip() == time_str:
                        slot_data = {**item, 'minute': minute}
                        break
                quarter_slots.append(slot_data)
            
            schedule_by_hour.append({
                'hour_24': hour,
                'hour_label': hour_label,
                'slots': quarter_slots
            })
        schedule = schedule_by_hour

        stats = {
            'analyzed': len(email_data),
            'actionable': len(tasks),
            'newsletters': 0
        }

        return render_template('planner_dashboard.html', 
                             date=datetime.date.today().strftime("%A, %B %d"),
                             summary=summary,
                             tasks=tasks,
                             schedule=schedule,
                             stats=stats,
                             emails=email_data)

    except Exception as e:
        # If token expired or other error, clear session and re-login
        logger.error(f"Error accessing dashboard: {e}", exc_info=True)
        # session.pop('credentials', None) # Commented out for debugging
        return f"An error occurred: {str(e)} <a href='/experiments/planner/logout'>Logout</a>"

@daily_planner_bp.route('/sync_schedule', methods=['POST'])
def sync_schedule():
    """Sync the confirmed schedule to Google Calendar"""
    if 'credentials' not in session:
        return {'success': False, 'error': 'Not authenticated'}, 401
    
    try:
        # Build service using credentials from session
        calendar_service = get_calendar_service(session['credentials'])
        
        # Parse the schedule from request
        data = request.json
        scheduled_tasks = data.get('tasks', [])
        
        if not scheduled_tasks:
            return {'success': False, 'error': 'No tasks to sync'}, 400
        
        # Sync tasks
        result = sync_tasks_to_calendar(calendar_service, scheduled_tasks)
        
        # Return result with appropriate mapping for frontend
        return {
            'success': True,
            'message': f"Created {result['events_created']} calendar events",
            'events': result['created_events'],
            'errors': result['errors'],
            'debug': {
                'tasks_received': result['tasks_received'],
                'events_created': result['events_created'],
                'errors_count': result['errors_count']
            }
        }
        
    except Exception as e:
        logger.error("Error syncing schedule", exc_info=True)
        return {'success': False, 'error': str(e)}, 500
