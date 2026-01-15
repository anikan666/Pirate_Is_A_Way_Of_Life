import os
import datetime
import json
from flask import Blueprint, render_template, redirect, url_for, session, request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

daily_planner_bp = Blueprint('daily_planner', __name__, template_folder='templates')

# Register auth routes from auth module
from experiments.daily_planner.auth import register_auth_routes
register_auth_routes(daily_planner_bp)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, 'credentials.json')
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly', 
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/calendar.events',  # For syncing schedule
    'openid'
]

# Debug Environment Loading
provider = os.environ.get('LLM_PROVIDER', 'Not Set')
print(f"DEBUG: LLM_PROVIDER is currently: '{provider}'")
if provider == 'gemini':
    key_status = "Set" if os.environ.get('GEMINI_API_KEY') else "Missing"
    print(f"DEBUG: GEMINI_API_KEY is: {key_status}")
elif provider == 'anthropic':
    key_status = "Set" if os.environ.get('ANTHROPIC_API_KEY') else "Missing"
    print(f"DEBUG: ANTHROPIC_API_KEY is: {key_status}")

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
        creds = Credentials(**session['credentials'])
        service = build('gmail', 'v1', credentials=creds)
        
        # 1. Fetch recent emails (last 3 days to catch older tasks)
        # 1. Fetch emails from specific label "Tasks to be tracked"
        # We search for the label explicitly. NO DATE FILTER as requested.
        results = service.users().messages().list(userId='me', q='label:"Tasks to be tracked"', maxResults=20).execute()
        messages = results.get('messages', [])
        
        email_data = []
        if messages:
            for message in messages:
                # Fetch full format to get the payload body
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                payload = msg['payload']
                headers = payload['headers']
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Extract Body (Text/Plain preference)
                body = ""
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain':
                            import base64
                            data = part['body'].get('data')
                            if data:
                                body = base64.urlsafe_b64decode(data).decode('utf-8')
                                break
                elif 'body' in payload:
                    data = payload['body'].get('data')
                    if data:
                        import base64
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                
                # Fallback to snippet if body parsing failed
                if not body:
                    body = msg.get('snippet', '')

                email_data.append({'subject': subject, 'sender': sender, 'date': date_str, 'snippet': body})

        # DEBUG: Show user what the API is actually fetching
        print("\n--- GMAIL API DEBUG RESPONSE (Full Context) ---")
        if email_data:
            print(f"Fetched {len(email_data)} emails from 'Tasks to be tracked'. First entry body length: {len(email_data[0]['snippet'])}")
            # Print first 500 chars of first email body
            print(f"Body Preview:\n{email_data[0]['snippet'][:500]}...")
        else:
            print("Fetched 0 emails from 'Tasks to be tracked'.")
        print("-----------------------------------------------\n")

        # SHORT CIRCUIT: If no emails, don't ask AI to hallucinate
        if not email_data:
            return render_template('planner_dashboard.html', 
                             date=datetime.date.today().strftime("%A, %B %d"),
                             summary="You are all caught up! No new emails in the last 24 hours.",
                             tasks=[],
                             schedule=[],
                             stats={'analyzed': 0, 'actionable': 0, 'newsletters': 0},
                             emails=[])

        # 2. AI Planning Logic (Ollama or Gemini)
        # ---------------------------------------
        plan_data = None
        ai_error = None
        
        # Prepare the prompt
        # We pass the full body now, up to 2000 chars per email to avoid hitting token limits too fast
        email_text = "\n\n".join([f"EMAIL #{i+1}:\n- From: {e['sender']}\n- Subject: {e['subject']}\n- BODY:\n{e['snippet'][:2000]}" for i, e in enumerate(email_data)])
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

        provider = os.environ.get('LLM_PROVIDER', 'ollama').lower()
        print(f"Using AI Provider: {provider}")

        try:
            if provider == 'anthropic':
                # --- ANTHROPIC CLAUDE IMPLEMENTATION ---
                import anthropic
                
                api_key = os.environ.get('ANTHROPIC_API_KEY')
                if not api_key:
                    raise Exception("ANTHROPIC_API_KEY not found in environment variables.")
                
                client = anthropic.Anthropic(api_key=api_key)
                
                message = client.messages.create(
                    model="claude-haiku-4-5-20250514",
                    max_tokens=4096,
                    temperature=0,
                    system="You are an elite Executive Assistant. Output only valid JSON.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Extract text content
                clean_text = message.content[0].text
                # Strip markdown if present
                clean_text = clean_text.replace('```json', '').replace('```', '').strip()
                plan_data = json.loads(clean_text)
                print("Successfully generated plan with Anthropic Claude Haiku!")

            elif provider == 'gemini':
                # --- GOOGLE GEMINI IMPLEMENTATION ---
                import google.generativeai as genai
                
                api_key = os.environ.get('GEMINI_API_KEY')
                if not api_key:
                    raise Exception("GEMINI_API_KEY not found in environment variables.")
                
                genai.configure(api_key=api_key)
                
                # List of models to try in order of preference
                candidates = [
                    'gemini-1.5-flash',
                    'gemini-1.5-flash-001',
                    'gemini-1.5-pro',
                    'gemini-2.0-flash-exp',
                    'gemini-pro'
                ]
                
                response = None
                last_error = None
                
                for model_name in candidates:
                    try:
                        print(f"DEBUG: Attempting to use model: {model_name}")
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(prompt)
                        break # Success!
                    except Exception as e:
                        print(f"DEBUG: Failed with {model_name}: {e}")
                        last_error = e
                
                if not response:
                    raise last_error
                
                # Gemini often wraps JSON in markdown code blocks, strip them
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                plan_data = json.loads(clean_text)
                print("Successfully generated plan with Google Gemini!")

            else:
                # --- LOCAL OLLAMA IMPLEMENTATION ---
                import requests
                # We use 'llama3' by default, fallback to 'mistral' if needed
                response = requests.post('http://localhost:11434/api/generate', json={
                    "model": "llama3", 
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }, timeout=30) 
                
                if response.status_code == 200:
                    result = response.json()
                    plan_data = json.loads(result['response'])
                    print("Successfully generated plan with Local LLM (Ollama)!")
                else:
                    ai_error = f"Ollama returned error: {response.status_code}"

        except Exception as e:
            import traceback
            print(f"\n{'='*60}")
            print(f"AI Generation Error ({provider})")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e}")
            print(f"Traceback:")
            traceback.print_exc()
            print(f"{'='*60}\n")
            ai_error = f"AI Error: {str(e)}"
            # Fallback to Mock Data so the app allows functions
            print("falling back to MOCK AI data for demo purposes...")

        # 3. Final Data Preparation (Real or Mock)
        if not plan_data:
            # ROBUST FALLBACK - Generate tasks from emails with source_email_id for deep linking
            summary = f"⚠️ AI unavailable. Showing {len(email_data)} emails as tasks. Drag to schedule."
            
            # Parse sender name from email format "Name <email@domain.com>"
            def extract_sender_name(sender_str):
                if '<' in sender_str:
                    return sender_str.split('<')[0].strip().strip('"')
                return sender_str.split('@')[0] if '@' in sender_str else sender_str
            
            tasks = []
            for i, email in enumerate(email_data):
                sender_name = extract_sender_name(email['sender'])
                tasks.append({
                    'title': email['subject'][:80],  # Truncate long subjects
                    'description': f"Email from {sender_name}",
                    'people': [sender_name],
                    'action_type': 'Do',  # Default to direct action in fallback
                    'assignee': 'You',
                    'urgency': 'High' if i < 3 else 'Normal',
                    'timeline_context': 'Check email for details',
                    'source_email_id': i + 1,  # 1-indexed for deep linking
                    'source': 'Fallback'
                })
            
            # Empty schedule - let user drag items
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
            'analyzed': len(messages),
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
        print(f"Error: {e}")
        # session.pop('credentials', None) # Commented out for debugging
        return f"An error occurred: {str(e)} <a href='/experiments/planner/logout'>Logout</a>"

@daily_planner_bp.route('/sync_schedule', methods=['POST'])
def sync_schedule():
    """Sync the confirmed schedule to Google Calendar"""
    if 'credentials' not in session:
        return {'success': False, 'error': 'Not authenticated'}, 401
    
    try:
        creds = Credentials(**session['credentials'])
        
        # Debug: Log the scopes we have
        print(f"\n=== CALENDAR SYNC AUTH DEBUG ===")
        print(f"Credentials scopes type: {type(creds.scopes)}")
        print(f"Credentials scopes value: {creds.scopes}")
        
        # TEMPORARILY BYPASSED: Check if we have calendar scope
        # The scope check was preventing events from being created.
        # Let the Calendar API call fail with a proper error if permissions are missing.
        has_calendar_scope = True  # Bypass for debugging
        if creds.scopes:
            for scope in creds.scopes:
                if 'calendar' in scope.lower():
                    print(f"Found calendar scope: {scope}")
                    break
        
        # Commented out: if not has_calendar_scope:
        #     ...
        
        print("Building calendar service...")
        calendar_service = build('calendar', 'v3', credentials=creds)
        print("Calendar service built successfully!")
        
        # Parse the schedule from request
        data = request.json
        print(f"\n=== SYNC SCHEDULE DEBUG ===")
        print(f"Raw request data: {data}")
        scheduled_tasks = data.get('tasks', [])
        print(f"Parsed scheduled_tasks: {scheduled_tasks}")
        print(f"Number of tasks: {len(scheduled_tasks)}")
        
        if not scheduled_tasks:
            print("ERROR: No tasks in request!")
            return {'success': False, 'error': 'No tasks to sync'}, 400
        
        # Get today's date for creating events
        today = datetime.date.today()
        created_events = []
        errors_list = []  # Track errors to return in response
        
        for task in scheduled_tasks:
            # Parse time slot (e.g., "9:00 AM", "1:00 PM")
            time_str = task.get('time', '')
            title = task.get('title', 'Untitled Task')
            duration_minutes = task.get('duration', 60)  # Default 1 hour
            
            print(f"\n--- Processing task ---")
            print(f"Time: '{time_str}', Title: '{title}', Duration: {duration_minutes}")
            
            # Parse time
            try:
                import re
                match = re.match(r'(\d+):(\d+)\s*(AM|PM)', time_str, re.IGNORECASE)
                if not match:
                    error_msg = f"Time regex did not match for '{time_str}'"
                    print(f"ERROR: {error_msg}")
                    errors_list.append(error_msg)
                    continue
                print(f"Time parsed successfully: hour={match.group(1)}, min={match.group(2)}, period={match.group(3)}")
                    
                hour = int(match.group(1))
                minute = int(match.group(2))
                period = match.group(3).upper()
                
                if period == 'PM' and hour != 12:
                    hour += 12
                elif period == 'AM' and hour == 12:
                    hour = 0
                
                # Create start and end times
                start_dt = datetime.datetime.combine(today, datetime.time(hour, minute))
                end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
                
                # Create Google Calendar event
                event = {
                    'summary': title,
                    'description': f'Created by Flow State Daily Planner',
                    'start': {
                        'dateTime': start_dt.isoformat(),
                        'timeZone': 'Asia/Kolkata',  # TODO: Get from user settings
                    },
                    'end': {
                        'dateTime': end_dt.isoformat(),
                        'timeZone': 'Asia/Kolkata',
                    },
                }
                
                print(f"Calendar event payload: {event}")
                created_event = calendar_service.events().insert(calendarId='primary', body=event).execute()
                created_events.append({
                    'id': created_event.get('id'),
                    'title': title,
                    'link': created_event.get('htmlLink')
                })
                print(f"SUCCESS: Created calendar event: {title} at {time_str}")
                
            except Exception as e:
                import traceback
                error_msg = f"Error creating '{title}': {type(e).__name__}: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                errors_list.append(error_msg)
                continue
        
        return {
            'success': True,
            'message': f'Created {len(created_events)} calendar events',
            'events': created_events,
            'errors': errors_list,  # Include errors so frontend can show them
            'debug': {
                'tasks_received': len(scheduled_tasks),
                'events_created': len(created_events),
                'errors_count': len(errors_list)
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}, 500
