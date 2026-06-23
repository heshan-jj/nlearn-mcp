import time
import re
from dataclasses import dataclass
from typing import List, Optional, Set
import logging

from auth.session import session_scope, get_base_url
from utils.debug import save_debug_text
from utils.validation import validate_days

logger = logging.getLogger(__name__)

_ACTIVE_COURSE_IDS_CACHE_TTL_S = 300  # 5 minutes
TIMELINE_EVENT_LIMIT = 50
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
    - `limitnum`: 100
     - `timesortfrom`: unix timestamp (start)
     - `timesortto`: unix timestamp (end) [only for past events]
     - `limittononsuspendedevents`: True
"""

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
        save_debug_text("dashboard_no_sesskey", resp.text)
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
    if not isinstance(ac_data, list) or not ac_data or ac_data[0].get("error"):
        logger.error(
            "Error fetching active courses: %s",
            (ac_data[0].get("error") if ac_data and isinstance(ac_data, list) and ac_data else None),
        )
        save_debug_text("active_courses_error", ac_resp_text)
        raise RuntimeError("Failed to fetch active courses from Moodle")

    courses = ac_data[0].get("data", {}).get("courses")
    if not isinstance(courses, list):
        save_debug_text("active_courses_unexpected_shape", ac_resp_text)
        raise RuntimeError("Moodle active courses response had an unexpected shape")

    for course in courses:
        course_id = course.get("id") if isinstance(course, dict) else None
        if course_id is not None:
            active_course_ids.add(course_id)

    # Cache successful fetches (even if the set is empty).
    _ACTIVE_COURSE_IDS_CACHE[cache_key] = (time.time(), active_course_ids)

    return active_course_ids

def _fetch_deadlines_from_api(days: int, is_past: bool = False) -> List[Deadline]:
    """
    Helper function to authenticate and fetch deadlines/calendar events from Moodle AJAX API.
    Handles the common login flow, active course verification, AJAX payload structure,
    and event filtering/parsing logic.
    """
    days = validate_days(days)

    with session_scope() as client:
        base_url = get_base_url()
        
        # 1. Fetch dashboard to grab sesskey
        logger.info("Fetching dashboard to retrieve sesskey...")
        sesskey = _get_sesskey(client, base_url)
        logger.info("Found sesskey.")
        
        # Fetch active courses to filter by
        logger.info("Fetching active courses...")
        active_course_ids = _get_active_course_ids(client, base_url, sesskey)
        logger.info(f"Found {len(active_course_ids)} active courses.")
        
        # 2. Fetch events via Moodle's AJAX API
        ajax_url = f"{base_url}/lib/ajax/service.php?sesskey={sesskey}&info=core_calendar_get_action_events_by_timesort"
        current_time = int(time.time())
        window_seconds = days * 24 * 60 * 60
        
        if is_past:
            timesortfrom = current_time - window_seconds
            timesortto = current_time
        else:
            timesortfrom = current_time
            timesortto = None
            
        args = {
            "limitnum": TIMELINE_EVENT_LIMIT,
            "timesortfrom": timesortfrom,
            "limittononsuspendedevents": True
        }
        if timesortto is not None:
            args["timesortto"] = timesortto
            
        payload = [{
            "index": 0,
            "methodname": "core_calendar_get_action_events_by_timesort",
            "args": args
        }]
        
        logger.info(f"Fetching timeline events (is_past={is_past})...")
        ajax_resp = client.post(ajax_url, json=payload)
        ajax_resp.raise_for_status()
        ajax_resp_text = ajax_resp.text
        data = ajax_resp.json()
        
        if not isinstance(data, list) or not data or data[0].get('error'):
            logger.error(f"Error fetching timeline: {data[0] if data else 'Empty response'}")
            save_debug_text("timeline_ajax_error", ajax_resp_text)
            raise RuntimeError("Failed to fetch timeline events from Moodle")
            
        events = data[0].get("data", {}).get("events")
        if not isinstance(events, list):
            save_debug_text("timeline_unexpected_shape", ajax_resp_text)
            raise RuntimeError("Moodle timeline response had an unexpected shape")

        if len(events) >= TIMELINE_EVENT_LIMIT:
            logger.warning(
                "Moodle returned %s timeline events, which reaches the configured limit; results may be truncated.",
                TIMELINE_EVENT_LIMIT,
            )

        deadlines = []
        
        for event in events:
            if not isinstance(event, dict):
                logger.warning("Skipping timeline event with unexpected shape.")
                continue

            due_date = event.get('timesort', 0)
            
            # Python-side validation to ensure timing window bounds
            if is_past:
                if due_date < timesortfrom:
                    continue
            else:
                end_time = current_time + window_seconds
                if due_date > end_time:
                    continue
                    
            course = event.get('course', {})
            if not isinstance(course, dict):
                course = {}
            course_id = course.get('id')
            
            # Filter out events from non-active (hidden/past) courses
            if course_id not in active_course_ids:
                continue
                
            action = event.get('action', {})
            if not isinstance(action, dict):
                action = {}
            
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


def get_deadlines(days: int = 14) -> List[Deadline]:
    """
    Get upcoming deadlines from the user's NLearn/Moodle dashboard.
    """
    return _fetch_deadlines_from_api(days=days, is_past=False)


def get_past_events(days: int = 60) -> List[Deadline]:
    """
    Get past/missed deadlines from the user's NLearn/Moodle dashboard.
    """
    return _fetch_deadlines_from_api(days=days, is_past=True)

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
