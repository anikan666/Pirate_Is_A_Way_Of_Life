"""
Gmail Service module for Daily Planner.
Handles email fetching and parsing from Gmail API.
"""
import base64
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Constants
from experiments.daily_planner.config import (
    EMAIL_BODY_MAX_LENGTH, 
    MAX_RESULTS, 
    GMAIL_LABEL
)


def get_gmail_service(credentials_dict: dict):
    """
    Build and return a Gmail API service from credentials dict.
    
    Args:
        credentials_dict: Session credentials dictionary with token, refresh_token, etc.
        
    Returns:
        Gmail API service resource.
    """
    creds = Credentials(**credentials_dict)
    return build('gmail', 'v1', credentials=creds)


def fetch_emails_from_label(service, label: str = GMAIL_LABEL, max_results: int = MAX_RESULTS) -> list:
    """
    Fetch emails from a specific Gmail label.
    
    Args:
        service: Gmail API service resource.
        label: Gmail label to fetch from (default: 'Tasks to be tracked').
        max_results: Maximum number of emails to fetch (default: 20).
        
    Returns:
        List of email data dictionaries with subject, sender, date, snippet/body.
    """
    logger.info(f"Fetching emails from label: '{label}' (max: {max_results})")
    
    # Fetch email IDs from the specified label
    results = service.users().messages().list(
        userId='me', 
        q=f'label:"{label}"', 
        maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    logger.info(f"Found {len(messages)} messages")
    
    email_data = []
    if not messages:
        return email_data
    
    for message in messages:
        email_info = _parse_email_message(service, message['id'])
        if email_info:
            email_data.append(email_info)
    
    return email_data


def _parse_email_message(service, message_id: str) -> dict:
    """
    Fetch and parse a single email message.
    
    Args:
        service: Gmail API service resource.
        message_id: The Gmail message ID.
        
    Returns:
        Dictionary with email data (subject, sender, date, snippet/body).
    """
    try:
        msg = service.users().messages().get(
            userId='me', 
            id=message_id, 
            format='full'
        ).execute()
        
        payload = msg['payload']
        headers = payload['headers']
        
        subject = _get_header_value(headers, 'Subject', 'No Subject')
        sender = _get_header_value(headers, 'From', 'Unknown')
        date_str = _get_header_value(headers, 'Date', '')
        
        # Extract body content
        body = _extract_body(payload)
        
        # Fallback to snippet if body parsing failed
        if not body:
            body = msg.get('snippet', '')
        
        return {
            'subject': subject,
            'sender': sender,
            'date': date_str,
            'snippet': body
        }
        
    except Exception as e:
        logger.error(f"Error parsing email {message_id}: {e}")
        return None


def _get_header_value(headers: list, name: str, default: str = '') -> str:
    """
    Get a header value from email headers list.
    
    Args:
        headers: List of email header dictionaries.
        name: Header name to find (e.g., 'Subject', 'From').
        default: Default value if header not found.
        
    Returns:
        Header value or default.
    """
    return next((h['value'] for h in headers if h['name'] == name), default)


def _extract_body(payload: dict) -> str:
    """
    Extract the body text from an email payload.
    Prefers text/plain MIME type.
    
    Args:
        payload: Gmail message payload dictionary.
        
    Returns:
        Decoded body text or empty string.
    """
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
    elif 'body' in payload:
        data = payload['body'].get('data')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    return body


def extract_sender_name(sender_str: str) -> str:
    """
    Parse sender name from email format "Name <email@domain.com>".
    
    Args:
        sender_str: Raw sender string from email header.
        
    Returns:
        Extracted sender name.
    """
    if '<' in sender_str:
        return sender_str.split('<')[0].strip().strip('"')
    return sender_str.split('@')[0] if '@' in sender_str else sender_str
