import os
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from bs4 import BeautifulSoup
import httpx
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COOKIES_FILE = Path(__file__).parent / "cookies.json"

def get_base_url():
    url = os.environ.get("NLEARN_URL")
    if not url:
        raise ValueError("NLEARN_URL environment variable is not set")
    return url.rstrip('/')

def load_cookies():
    if COOKIES_FILE.exists():
        try:
            with open(COOKIES_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")
    return None

def save_cookies(client: httpx.Client):
    cookies_to_save = {}
    for name, value in client.cookies.items():
        if name == "MoodleSession" or name.startswith("MOODLEID1_"):
            cookies_to_save[name] = value
    
    try:
        COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies_to_save, f)
        logger.info("Session cookies saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")

def validate_session(client: httpx.Client, base_url: str) -> bool:
    """Validate if the current session is still alive."""
    try:
        # A lightweight probe to check if we are logged in.
        # usually accessing the dashboard or user profile works.
        response = client.get(f"{base_url}/my/", follow_redirects=False)
        # If we get redirected to login, session is dead.
        if response.status_code in (302, 303) and "login" in response.headers.get("Location", ""):
            return False
        
        # Alternatively, check page content
        if "login/index.php" in response.text:
            return False
            
        return True
    except Exception as e:
        logger.error(f"Session validation failed: {e}")
        return False

def login(client: httpx.Client, base_url: str):
    """Perform the actual login flow."""
    username = os.environ.get("NLEARN_USERNAME")
    password = os.environ.get("NLEARN_PASSWORD")
    
    if not username or not password:
        raise ValueError("NLEARN_USERNAME and NLEARN_PASSWORD environment variables must be set")
        
    login_url = f"{base_url}/login/index.php"
    
    # 1. GET login page to scrape logintoken
    logger.info("Fetching login page...")
    response = client.get(login_url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.find("input", {"name": "logintoken"})
    
    if not token_input:
        raise ValueError("Could not find logintoken on the login page")
        
    logintoken = token_input.get("value")
    
    # 2. POST login page
    payload = {
        "username": username,
        "password": password,
        "logintoken": logintoken,
        "rememberusername": "1",
        "anchor": ""
    }
    
    logger.info("Submitting login credentials...")
    post_response = client.post(login_url, data=payload, follow_redirects=True)
    post_response.raise_for_status()

    if "login/index.php" in str(post_response.url):
        raise Exception("Login failed: still on login page after POST")

    if "MoodleSession" not in client.cookies:
        raise Exception("Login failed: MoodleSession cookie not set")
    
    save_cookies(client)
    logger.info("Login successful")

def _ensure_authenticated(client: httpx.Client) -> None:
    """Populate client cookies so requests run as a logged-in session."""
    base_url = get_base_url()

    cookies = load_cookies()
    if cookies:
        client.cookies.update(cookies)
        logger.info("Loaded cached cookies. Validating session...")

        if validate_session(client, base_url):
            logger.info("Session is valid.")
            return

        logger.info("Session is dead. Re-authenticating...")
    else:
        logger.info("No cached cookies found. Authenticating...")

    client.cookies.clear()
    login(client, base_url)

@contextmanager
def session_scope():
    """
    Yields an httpx.Client with valid cookies; closes the client when done.
    """
    client = httpx.Client()
    try:
        _ensure_authenticated(client)
        yield client
    finally:
        client.close()

if __name__ == "__main__":
    # Test the session logic
    with session_scope() as session:
        print("Session ready. Cookies:", dict(session.cookies))
