import os
import json
import logging
import time
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


class RetryingClient:
    """
    Thin wrapper around `httpx.Client` that retries transient failures.

    This keeps scraper code unchanged (they already use `client.get`/`client.post`)
    while making requests more resilient to flaky NLearn/Moodle behavior.
    """

    def __init__(
        self,
        client: httpx.Client,
        *,
        attempts: int = 3,
        backoff_factor_s: float = 0.75,
        max_delay_s: float = 6.0,
    ):
        self._client = client
        self._attempts = attempts
        self._backoff_factor_s = backoff_factor_s
        self._max_delay_s = max_delay_s

    @property
    def cookies(self):
        return self._client.cookies

    def close(self) -> None:
        self._client.close()

    def __getattr__(self, item):
        return getattr(self._client, item)

    def _should_retry_response(self, response: httpx.Response) -> bool:
        # Retry on rate limit and server errors.
        return response.status_code == 429 or response.status_code >= 500

    def _sleep_before_retry(self, attempt: int) -> None:
        # Exponential backoff: backoff_factor * 2^(attempt-1)
        delay_s = self._backoff_factor_s * (2 ** (attempt - 1))
        time.sleep(min(delay_s, self._max_delay_s))

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        last_exc: Exception | None = None

        for attempt in range(1, self._attempts + 1):
            try:
                resp = self._client.request(method, url, **kwargs)
                if self._should_retry_response(resp) and attempt < self._attempts:
                    logger.warning(
                        "Request got retryable response (status=%s) attempt=%s/%s: %s",
                        resp.status_code,
                        attempt,
                        self._attempts,
                        url,
                    )
                    self._sleep_before_retry(attempt)
                    continue

                return resp
            except httpx.RequestError as e:
                last_exc = e
                if attempt >= self._attempts:
                    raise

                logger.warning(
                    "Request failed (attempt=%s/%s) %s %s: %s",
                    attempt,
                    self._attempts,
                    method,
                    url,
                    str(e),
                )
                self._sleep_before_retry(attempt)

        # Should be unreachable; re-raise last exception if something went wrong.
        if last_exc:
            raise last_exc
        raise RuntimeError("RetryingClient.request exhausted retries without error.")

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

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
    retry_client = RetryingClient(client)
    try:
        _ensure_authenticated(retry_client)
        yield retry_client
    finally:
        client.close()

if __name__ == "__main__":
    # Test the session logic
    with session_scope() as session:
        print("Session ready. Cookies:", dict(session.cookies))
