import time
import re
from dataclasses import dataclass
from typing import List, Optional, Set
import logging
from pathlib import Path
import tempfile
import uuid

from auth.session import session_scope, get_base_url

logger = logging.getLogger(__name__)

DEBUG_DIR = Path(tempfile.gettempdir()) / "debug"

_ACTIVE_COURSE_IDS_CACHE_TTL_S = 300  # 5 minutes
# Keyed by (base_url, sesskey) because sesskey can change during an auth refresh.
_ACTIVE_COURSE_IDS_CACHE: dict[tuple[str, str], tuple[float, Set[int]]] = {}

"""
Moodle AJAX endpoints used (via `lib/ajax/service.php`)

We scrape a `sesskey` token from the dashboard (`GET {base_url}/my/`) and then
call Moodle's JSON endpoint:

`POST {base_url}/lib/ajax/service.php?sesskey={sesskey}&info=<component>`

For each call we send a batch payload list with:

- `index`: request index within the batch
- `methodname`: Moodle service method name
- `args`: method-specific arguments

Endpoints in this file:

1) Active courses (filtering)
   - URL `info` component:
     `core_course_get_enrolled_courses_by_timeline_classification`
   - Payload methodname:
     `core_course_get_enrolled_courses_by_timeline_classification`
   - Args used:
     - `offset`: 0
     - `limit`: 0
     - `classification`: "inprogress"
     - `sort`: "fullname"

2) Timeline events
   - URL `info` component:
     `core_calendar_get_action_events_by_timesort`
   - Payload methodname:
     `core_calendar_get_action_events_by_timesort`
   - Args used:
     - `limitnum`: 50
     - `timesortfrom`: unix timestamp (start)
     - `timesortto`: unix timestamp (end) [only for past events]
     - `limittononsuspendedevents`: True
"""


def _save_debug_text(context: str, text: str, *, max_chars: int = 200_000) -> None:
    """
    Save scraper debug output into a temp `debug/` directory.

    Intended for troubleshooting cases like "sesskey not found" or "scrape error".
    """
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        fname = f"{context}_{int(time.time())}_{uuid.uuid4().hex}.html"
        path = DEBUG_DIR / fname
        path.write_text(text[:max_chars], encoding="utf-8", errors="replace")
        logger.info("Saved debug artifact: %s", path)
    except Exception as e:
        logger.warning("Failed to save debug artifact (%s): %s", context, e)

@dataclass
class Deadline:
    id: int
    name: str
    course_name: str
    due_date: int  # Unix timestamp
    url: str
    action_name: Optional[str] = None
    action_url: Optional[str] = None

def _get_sesskey(client, base_url: str) -> str:
    resp = client.get(f"{base_url}/my/")
    resp.raise_for_status()

    sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
    if not sesskey_match:
        sesskey_match = re.search(r'name="sesskey" value="([^"]+)"', resp.text)

    if not sesskey_match:
        logger.error(
            "Could not find sesskey in dashboard HTML (first 2000 chars): %s",
            resp.text[:2000],
        )
        _save_debug_text("dashboard_no_sesskey", resp.text)
        raise ValueError("Could not find sesskey in dashboard HTML")

    return sesskey_match.group(1)

def _get_active_course_ids(client, base_url: str, sesskey: str) -> Set[int]:
    cache_key = (base_url, sesskey)
    cached = _ACTIVE_COURSE_IDS_CACHE.get(cache_key)
    if cached is not None:
        fetched_at, ids = cached
        if time.time() - fetched_at <= _ACTIVE_COURSE_IDS_CACHE_TTL_S:
            logger.info(
                "Active course IDs cache hit (courses=%s, ttl_s=%s).",
                len(ids),
                _ACTIVE_COURSE_IDS_CACHE_TTL_S,
            )
            return ids

    active_courses_url = f"{base_url}/lib/ajax/service.php?sesskey={sesskey}&info=core_course_get_enrolled_courses_by_timeline_classification"
    active_courses_payload = [{
        "index": 0,
        "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
        "args": {
            "offset": 0,
            "limit": 0,
            "classification": "inprogress",
            "sort": "fullname"
        }
    }]

    ac_resp = client.post(active_courses_url, json=active_courses_payload)
    ac_resp.raise_for_status()
    ac_resp_text = ac_resp.text
    ac_data = ac_resp.json()

    active_course_ids: Set[int] = set()
    if ac_data and not ac_data[0].get("error"):
        for course in ac_data[0]["data"]["courses"]:
            active_course_ids.add(course["id"])
        # Cache successful fetches (even if the set is empty).
        _ACTIVE_COURSE_IDS_CACHE[cache_key] = (time.time(), active_course_ids)
    else:
        logger.error(
            "Error fetching active courses: %s",
            (ac_data[0].get("error") if ac_data and isinstance(ac_data, list) and ac_data else None),
        )
        _save_debug_text("active_courses_error", ac_resp_text)

    return active_course_ids

def get_deadlines(days: int = 14) -> List[Deadline]:
    with session_scope() as client:
        base_url = get_base_url()
        
        # 1. Fetch dashboard to grab sesskey
        logger.info("Fetching dashboard to retrieve sesskey...")
        sesskey = _get_sesskey(client, base_url)
        logger.info(f"Found sesskey: {sesskey}")
        
        # Fetch active courses to filter by
        logger.info("Fetching active courses...")
        active_course_ids = _get_active_course_ids(client, base_url, sesskey)
                
        logger.info(f"Found {len(active_course_ids)} active courses.")
        
        # 2. Fetch timeline events via Moodle's AJAX API
        ajax_url = f"{base_url}/lib/ajax/service.php?sesskey={sesskey}&info=core_calendar_get_action_events_by_timesort"
        
        current_time = int(time.time())
        
        payload = [{
            "index": 0,
            "methodname": "core_calendar_get_action_events_by_timesort",
            "args": {
                "limitnum": 50,
                "timesortfrom": current_time,
                "limittononsuspendedevents": True
            }
        }]
        
        logger.info("Fetching timeline events...")
        ajax_resp = client.post(ajax_url, json=payload)
        ajax_resp.raise_for_status()
        ajax_resp_text = ajax_resp.text
        data = ajax_resp.json()
        
        if not data or data[0].get('error'):
            logger.error(f"Error fetching timeline: {data[0] if data else 'Empty response'}")
            _save_debug_text("timeline_ajax_error", ajax_resp_text)
            return []
            
        events = data[0]['data']['events']
        
        deadlines = []
        end_time = current_time + (days * 24 * 60 * 60)
        
        for event in events:
            due_date = event.get('timesort', 0)
            
            # Filter by configurable window
            if due_date > end_time:
                continue
                
            course = event.get('course', {})
            course_id = course.get('id')
            
            # Filter out events from non-active (hidden/past) courses
            # If the user has a lot of missed stuff from older courses, they might want this disabled.
            # For now, we'll keep it but the 180 day window will catch more.
            if active_course_ids and course_id not in active_course_ids:
                continue
                
            action = event.get('action', {})
            
            deadline = Deadline(
                id=event.get('id'),
                name=event.get('name', ''),
                course_name=course.get('fullname', 'Unknown Course'),
                due_date=due_date,
                url=event.get('url', ''),
                action_name=action.get('name') if action else None,
                action_url=action.get('url') if action else None
            )
            deadlines.append(deadline)
            
        return deadlines

def get_past_events(days: int = 60) -> List[Deadline]:
    with session_scope() as client:
        base_url = get_base_url()
        
        # 1. Fetch dashboard to grab sesskey
        sesskey = _get_sesskey(client, base_url)
        
        # Fetch active courses to filter by
        logger.info("Fetching active courses...")
        active_course_ids = _get_active_course_ids(client, base_url, sesskey)

        # 2. Fetch past events
        current_time = int(time.time())
        start_time = current_time - (days * 24 * 60 * 60)
        
        ajax_url = f"{base_url}/lib/ajax/service.php?sesskey={sesskey}&info=core_calendar_get_action_events_by_timesort"
        payload = [{
            "index": 0,
            "methodname": "core_calendar_get_action_events_by_timesort",
            "args": {
                "limitnum": 50,
                "timesortfrom": start_time,
                "timesortto": current_time,
                "limittononsuspendedevents": True
            }
        }]
        
        logger.info(f"Fetching past events from the last {days} days...")
        ajax_resp = client.post(ajax_url, json=payload)
        ajax_resp.raise_for_status()
        ajax_resp_text = ajax_resp.text
        data = ajax_resp.json()
        
        if not data or data[0].get('error'):
            return []
            
        events = data[0]['data']['events']
        deadlines = []
        
        for event in events:
            due_date = event.get('timesort', 0)
            
            # Filter by window in Python
            if due_date < start_time:
                continue

            course_id = event.get('course', {}).get('id')
            if active_course_ids and course_id not in active_course_ids:
                continue
                
            action = event.get('action', {})
            deadline = Deadline(
                id=event.get('id'),
                name=event.get('name', ''),
                course_name=event.get('course', {}).get('fullname', 'Unknown Course'),
                due_date=due_date,
                url=event.get('url', ''),
                action_name=action.get('name') if action else None,
                action_url=action.get('url') if action else None
            )
            deadlines.append(deadline)
            
        return deadlines

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    deadlines = get_deadlines(14)
    print(f"\nFound {len(deadlines)} upcoming deadlines in the next 14 days:")
    for d in deadlines:
        print(f" - [{time.strftime('%Y-%m-%d', time.localtime(d.due_date))}] {d.course_name}: {d.name}")
        if d.action_url:
            print(f"     -> Action: {d.action_name} ({d.action_url})")
        else:
            print(f"     -> URL: {d.url}")
