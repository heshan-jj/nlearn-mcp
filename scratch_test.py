import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from auth.session import get_session, get_base_url
import re
import json

def test():
    client = get_session()
    base_url = get_base_url()
    
    resp = client.get(f"{base_url}/my/")
    
    sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
    if not sesskey_match:
        print("Sesskey not found")
        # Try to find it in input forms
        sesskey_match = re.search(r'name="sesskey" value="([^"]+)"', resp.text)
        
    if sesskey_match:
        sesskey = sesskey_match.group(1)
        print(f"Found sesskey: {sesskey}")
        
        # Try timeline AJAX endpoint
        # Moodle 3.x/4.x timeline endpoint
        ajax_url = f"{base_url}/lib/ajax/service.php?sesskey={sesskey}&info=core_calendar_get_action_events_by_timesort"
        payload = [{
            "index": 0,
            "methodname": "core_calendar_get_action_events_by_timesort",
            "args": {
                "limitnum": 20,
                "timesortfrom": 0,
                "limittononsuspendedevents": True
            }
        }]
        print("Calling AJAX endpoint...")
        ajax_resp = client.post(ajax_url, json=payload)
        print("Status code:", ajax_resp.status_code)
        
        try:
            data = ajax_resp.json()
            print("Response JSON snippet:", json.dumps(data, indent=2)[:500])
        except Exception as e:
            print("Failed to parse JSON:", e)
            print(ajax_resp.text[:500])
    else:
        print("Could not find sesskey. HTML snippet:")
        print(resp.text[:1000])

if __name__ == "__main__":
    test()
