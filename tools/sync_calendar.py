from datetime import datetime, timezone
from typing import List, Dict, Any
from scrapers.timeline import get_deadlines


def get_deadlines_for_sync(days: int = 14) -> List[Dict[str, Any]]:
    """
    Retrieves upcoming deadlines formatted explicitly for Claude's Google Calendar integration.
    This allows Claude to read the deadlines and automatically create Calendar events.

    Args:
        days (int): Number of days ahead to fetch deadlines for (default 14).

    Returns:
        List[Dict[str, Any]]: A list of calendar-ready dicts containing:
            - title
            - due_date (ISO 8601 UTC format)
            - course
            - description
            - reminder_minutes
    """
    deadlines = get_deadlines(days=days)

    return [
        {
            "title": f"{d.course_name} - {d.name}",
            "due_date": datetime.fromtimestamp(d.due_date, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "course": d.course_name,
            "description": (
                f"Course: {d.course_name}\n"
                f"Task: {d.name}\n"
                f"Submit via NLearn. Link: {d.action_url or d.url}"
            ),
            "reminder_minutes": 1440,  # 24hr prior reminder
        }
        for d in deadlines
    ]
