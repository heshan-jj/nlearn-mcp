from typing import List
import time
from scrapers.timeline import get_deadlines as fetch_deadlines

def get_upcoming_deadlines(days: int = 14) -> str:
    """
    Get a list of upcoming assignments and deadlines from the user's NLearn/Moodle dashboard.
    This fetches real-time data from the user's active courses.
    
    Args:
        days: The number of days into the future to look for deadlines. Default is 14.
    """
    try:
        deadlines = fetch_deadlines(days=days)
        
        if not deadlines:
            return f"You have no upcoming deadlines in the next {days} days. Great job!"
            
        result = [f"Found {len(deadlines)} upcoming deadlines in the next {days} days:\n"]
        
        for d in deadlines:
            date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(d.due_date))
            entry = f"- {d.name} (Course: {d.course_name})\n  Due: {date_str}\n  Link: {d.url}"
            if d.action_name and d.action_url:
                entry += f"\n  Action: {d.action_name} ({d.action_url})"
            result.append(entry)
            
        return "\n\n".join(result)
        
    except Exception as e:
        return f"Failed to retrieve deadlines: {str(e)}"
