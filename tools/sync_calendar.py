import datetime
from typing import List, Dict, Any
from scrapers.timeline import get_deadlines

def get_deadlines_for_sync(days: int = 14) -> List[Dict[str, Any]]:
    """
    Retrieves upcoming deadlines formatted explicitly for Claude's Google Calendar integration.
    This allows Claude to read the deadlines and automatically create Calendar events.
    
    Args:
        days (int): Number of days ahead to fetch deadlines for (default 14).
        
    Returns:
        List[Dict[str, Any]]: A list of dictionary objects structured for Calendar ingestion, containing:
            - title
            - due_date (ISO 8601 format)
            - course
            - description
            - reminder_minutes
    """
    deadlines = get_deadlines(days=days)
    sync_data = []
    
    for d in deadlines:
        # Convert unix timestamp to ISO 8601
        dt = datetime.datetime.fromtimestamp(d.due_date)
        iso_date = dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Build description
        action_link = d.action_url if d.action_url else d.url
        description = f"Course: {d.course_name}\nTask: {d.name}\nSubmit via NLearn. Link: {action_link}"
        
        sync_item = {
            "title": f"{d.course_name} - {d.name}",
            "due_date": iso_date,
            "course": d.course_name,
            "description": description,
            "reminder_minutes": 1440  # 24hr prior reminder
        }
        sync_data.append(sync_item)
        
    return sync_data
