import time
import re
from dataclasses import dataclass
from typing import List, Optional
import logging

from auth.session import session_scope, get_base_url

logger = logging.getLogger(__name__)

@dataclass
class Deadline:
    id: int
    name: str
    course_name: str
    due_date: int  # Unix timestamp
    url: str
    action_name: Optional[str] = None
    action_url: Optional[str] = None

def get_deadlines(days: int = 14) -> List[Deadline]:
    with session_scope() as client:
        base_url = get_base_url()
        
        # 1. Fetch dashboard to grab sesskey
        logger.info("Fetching dashboard to retrieve sesskey...")
        resp = client.get(f"{base_url}/my/")
        resp.raise_for_status()
        
        sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
        if not sesskey_match:
            sesskey_match = re.search(r'name="sesskey" value="([^"]+)"', resp.text)
            
        if not sesskey_match:
            raise ValueError("Could not find sesskey in dashboard HTML")
            
        sesskey = sesskey_match.group(1)
        logger.info(f"Found sesskey: {sesskey}")
        
        # Fetch active courses to filter by
        logger.info("Fetching active courses...")
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
        ac_data = ac_resp.json()
        
        active_course_ids = set()
        if ac_data and not ac_data[0].get('error'):
            for c in ac_data[0]['data']['courses']:
                active_course_ids.add(c['id'])
                
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
        
        data = ajax_resp.json()
        
        if not data or data[0].get('error'):
            logger.error(f"Error fetching timeline: {data[0] if data else 'Empty response'}")
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
        resp = client.get(f"{base_url}/my/")
        resp.raise_for_status()
        sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
        if not sesskey_match:
            sesskey_match = re.search(r'name="sesskey" value="([^"]+)"', resp.text)
        if not sesskey_match:
            raise ValueError("Could not find sesskey in dashboard HTML")
        sesskey = sesskey_match.group(1)
        
        # Fetch active courses to filter by
        logger.info("Fetching active courses...")
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
        ac_data = ac_resp.json()
        active_course_ids = {c['id'] for c in ac_data[0]['data']['courses']} if ac_data and not ac_data[0].get('error') else set()

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
