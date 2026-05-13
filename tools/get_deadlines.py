import datetime
from typing import List, Dict, Any
from scrapers.timeline import get_deadlines as fetch_deadlines, get_past_events as fetch_past_events


def _deadline_to_dict(d) -> Dict[str, Any]:
    """Convert a Deadline dataclass instance to a plain dict for tool output."""
    dt = datetime.datetime.fromtimestamp(d.due_date, tz=datetime.timezone.utc)
    return {
        "id": d.id,
        "name": d.name,
        "course_name": d.course_name,
        "due_date_unix": d.due_date,
        "due_date_iso": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": d.url,
        "action_name": d.action_name,
        "action_url": d.action_url,
    }


def get_upcoming_deadlines(days: int = 14) -> Dict[str, Any]:
    """
    Get structured upcoming deadlines from the user's NLearn/Moodle dashboard.

    Returns a dict with a summary and a list of deadline objects, so Claude can reason over them.
    """
    deadlines = fetch_deadlines(days=days)

    items: List[Dict[str, Any]] = [_deadline_to_dict(d) for d in deadlines]

    return {
        "window_days": days,
        "count": len(items),
        "has_deadlines": bool(items),
        "deadlines": items,
    }


def get_past_deadlines(days: int = 60) -> Dict[str, Any]:
    """
    Get structured past/missed deadlines from the user's NLearn/Moodle dashboard.

    Returns a dict with a summary and a list of deadline objects.
    """
    deadlines = fetch_past_events(days=days)

    items: List[Dict[str, Any]] = [_deadline_to_dict(d) for d in deadlines]

    return {
        "window_days": days,
        "count": len(items),
        "has_deadlines": bool(items),
        "deadlines": items,
    }

