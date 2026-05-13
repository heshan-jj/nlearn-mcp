# 🔧 Fixes Required

> Audit Date: 2026-05-12
> Project: nlearn mcp

---

## 🚨 Critical

- [ ] **Plaintext credentials in `.env` are exposed** — `.env`
  Your actual username (`whhjayakody`) and password (`Adn6%whh`) are sitting in a tracked-looking `.env` file. Confirm `.env` is in `.gitignore` (it is ✅), but double-check with `git status` that it has never been committed. Run `git log --all --full-history -- .env` to verify. If it was ever committed, rotate your password immediately and purge git history.

- [ ] **`cookies.json` may contain live session tokens** — `auth/cookies.json`
  The file is gitignored ✅ but it currently holds your active `MoodleSession` cookie. Anyone with local access to the machine can hijack the session. Keep this in mind if the repo ever gets zipped and shared.

- [ ] **`get_past_events` will crash if sesskey regex fails** — `scrapers/timeline.py:75`
  In `get_past_events`, the sesskey is extracted with `.group(1)` directly — no null check, unlike `get_deadlines` which handles it safely. If the regex fails, this throws an `AttributeError` with no helpful message.
  ```python
  # Current (unsafe)
  sesskey = re.search(r'"sesskey":"([^"]+)"', resp.text).group(1)
  
  # Fix
  match = re.search(r'"sesskey":"([^"]+)"', resp.text)
  if not match:
      raise ValueError("Could not find sesskey in dashboard HTML")
  sesskey = match.group(1)
  ```

- [ ] **`login()` failure detection is fragile** — `auth/session.py:80`
  The login success check looks for `"Invalid login"` in the response body — but Moodle may phrase errors differently depending on version/locale (e.g. `"Invalid credentials"`, `"Too many failed logins"`). A more reliable check is to verify that the `MoodleSession` cookie was set AND that the response URL is no longer the login page.
  ```python
  # More robust check
  if "login/index.php" in str(post_response.url):
      raise Exception("Login failed: still on login page after POST")
  ```

- [ ] **`sys.path.append` hacks in scrapers** — `scrapers/timeline.py:8-9`, `scrapers/assignments.py:8-9`
  Both scrapers manipulate `sys.path` to resolve imports. This works but breaks in some MCP server contexts and is a code smell. Fix by making the project a proper package with a `pyproject.toml` and installing it with `uv pip install -e .`, or add an `__init__.py` at the root.

---

## ⚠️ Non-Critical

- [ ] **No `__init__.py` in `auth/` or `utils/`** — `auth/`, `utils/`
  Without these, the packages rely on the `sys.path` hack to be importable. Add empty `__init__.py` files to both directories.

- [ ] **`get_assignment` tool has no input validation** — `tools/get_assignment.py`
  The tool accepts any string as `assignment_url` and passes it directly to `httpx`. There's no check that it's a valid NLearn URL. A typo or a prompt injection could cause it to make arbitrary HTTP requests.
  ```python
  base_url = get_base_url()
  if not assignment_url.startswith(base_url):
      return f"Error: URL must be from {base_url}"
  ```

- [ ] **httpx client is never closed** — `auth/session.py`, `scrapers/`
  `get_session()` returns an `httpx.Client` but it is never closed. Use a context manager or call `client.close()` after each tool invocation to avoid resource leaks.

- [ ] **`get_past_events` fetches `timesortfrom: 0`** — `scrapers/timeline.py:103`
  Passing `0` as `timesortfrom` asks Moodle for all events from the Unix epoch. Moodle may silently cap or reject this. Pass `start_time` instead of `0` for cleaner, more predictable results.

- [ ] **No `pyproject.toml` or `requirements.txt`** — root
  The project has no dependency manifest. Anyone cloning the repo (including future you) has no way to know what to install. Add a `pyproject.toml` with `uv` or at minimum a `requirements.txt`.
