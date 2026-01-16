"""
Calendar Service module for Daily Planner.
Handles Google Calendar sync operations.
"""
import re
import datetime
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Constants
from experiments.daily_planner.config import (
    DEFAULT_TIMEZONE, 
    DEFAULT_EVENT_DURATION_MINUTES
)


def get_calendar_service(credentials_dict: dict):
    """
    Build and return a Google Calendar API service from credentials dict.
    
    Args:
        credentials_dict: Session credentials dictionary with token, refresh_token, etc.
        
    Returns:
        Google Calendar API service resource.
    """
    creds = Credentials(**credentials_dict)
    return build('calendar', 'v3', credentials=creds)


def parse_time_string(time_str: str) -> tuple:
    """
    Parse a time string like "9:00 AM" or "1:30 PM" into hour and minute.
    
    Args:
        time_str: Time string in format "H:MM AM/PM".
        
    Returns:
        Tuple of (hour_24, minute) or (None, None) if parsing fails.
    """
    match = re.match(r'(\d+):(\d+)\s*(AM|PM)', time_str, re.IGNORECASE)
    if not match:
        logger.error(f"Failed to parse time string: '{time_str}'")
        return None, None
    
    hour = int(match.group(1))
    minute = int(match.group(2))
    period = match.group(3).upper()
    
    # Convert to 24-hour format
    if period == 'PM' and hour != 12:
        hour += 12
    elif period == 'AM' and hour == 12:
        hour = 0
    
    return hour, minute


def create_calendar_event(
    service,
    title: str,
    start_time: datetime.datetime,
    duration_minutes: int = DEFAULT_EVENT_DURATION_MINUTES,
    description: str = 'Created by Flow State Daily Planner',
    timezone: str = DEFAULT_TIMEZONE
) -> dict:
    """
    Create a single event in Google Calendar.
    
    Args:
        service: Google Calendar API service resource.
        title: Event title/summary.
        start_time: Event start datetime.
        duration_minutes: Event duration in minutes.
        description: Event description text.
        timezone: Timezone for the event.
        
    Returns:
        Created event dict with id, title, and link, or None if failed.
    """
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    
    event_body = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': timezone,
        },
    }
    
    try:
        created_event = service.events().insert(
            calendarId='primary', 
            body=event_body
        ).execute()
        
        logger.info(f"Created calendar event: '{title}' at {start_time}")
        
        return {
            'id': created_event.get('id'),
            'title': title,
            'link': created_event.get('htmlLink')
        }
    except Exception as e:
        logger.error(f"Error creating calendar event '{title}': {e}")
        return None


def sync_tasks_to_calendar(
    service,
    tasks: list,
    date: datetime.date = None,
    timezone: str = DEFAULT_TIMEZONE
) -> dict:
    """
    Sync a list of scheduled tasks to Google Calendar.
    
    Args:
        service: Google Calendar API service resource.
        tasks: List of task dicts with 'time', 'title', and optional 'duration'.
        date: Date for events (defaults to today).
        timezone: Timezone for events.
        
    Returns:
        Dict with 'created_events', 'errors', and counts.
    """
    if date is None:
        date = datetime.date.today()
    
    created_events = []
    errors = []
    
    for task in tasks:
        time_str = task.get('time', '')
        title = task.get('title', 'Untitled Task')
        duration_minutes = task.get('duration', DEFAULT_EVENT_DURATION_MINUTES)
        
        logger.debug(f"Processing task: '{title}' at '{time_str}'")
        
        # Parse time string
        hour, minute = parse_time_string(time_str)
        if hour is None:
            error_msg = f"Failed to parse time '{time_str}' for task '{title}'"
            errors.append(error_msg)
            continue
        
        # Create datetime for event
        start_time = datetime.datetime.combine(
            date, 
            datetime.time(hour, minute)
        )
        
        # Create the calendar event
        event = create_calendar_event(
            service=service,
            title=title,
            start_time=start_time,
            duration_minutes=duration_minutes,
            timezone=timezone
        )
        
        if event:
            created_events.append(event)
        else:
            errors.append(f"Failed to create event for '{title}'")
    
    return {
        'created_events': created_events,
        'errors': errors,
        'tasks_received': len(tasks),
        'events_created': len(created_events),
        'errors_count': len(errors)
    }


def check_calendar_scope(scopes: list) -> bool:
    """
    Check if the credentials include calendar scope.
    
    Args:
        scopes: List of OAuth scopes from credentials.
        
    Returns:
        True if calendar scope is present, False otherwise.
    """
    if not scopes:
        return False
    
    for scope in scopes:
        if 'calendar' in scope.lower():
            return True
    
    return False
