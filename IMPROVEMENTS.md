# 🚀 Suggested Improvements

> Audit Date: 2026-05-12
> Project: nlearn mcp

---

## Code Quality

- **Extract `sesskey` fetching into a shared utility** — Both `get_deadlines` and `get_past_events` in `timeline.py` duplicate the exact same logic: fetch `/my/`, regex for sesskey, fetch active courses. This is ~30 lines duplicated verbatim. Extract into a helper like `_get_sesskey(client, base_url)` and `_get_active_course_ids(client, base_url, sesskey)`.

- **Return structured data from tools, not formatted strings** — `tools/get_deadlines.py` formats deadlines into a human-readable string before returning. This is fine for now but limits Claude's ability to reason over the data. Consider returning a structured list/dict and letting FastMCP serialize it — Claude handles structured tool outputs well.

- **Use `dataclass` or `TypedDict` for sync output** — `sync_calendar.py` returns a raw `Dict[str, Any]`. Defining a `CalendarEvent` dataclass or `TypedDict` would make the contract explicit and catch bugs earlier.

---

## Resilience & Error Handling

- **Add retry logic for network calls** — NLearn can be flaky (it's a university server). Wrap the key `httpx` calls in a simple retry loop (3 attempts, exponential backoff). The `tenacity` library makes this one decorator: `@retry(stop=stop_after_attempt(3), wait=wait_exponential())`.

- **Add a `refresh_session` MCP tool** — If the cached session expires mid-day, the user has no way to force a re-login without restarting the server. Expose a `refresh_session()` tool that clears `cookies.json` and re-authenticates on demand.

- **Screenshot-on-failure for scraping** — When the scraper fails to find a sesskey or PDF, it's hard to debug without seeing the HTML. Log the first 2000 chars of the response on failure, or save a debug HTML file to a `/tmp/debug/` directory.

---

## Security

- **Scope the `get_assignment` URL** — As noted in FIXES.md, validate that the URL belongs to the configured NLearn instance before making the request. This prevents the tool from being used as an SSRF vector via prompt injection.

- **Rotate credentials if `.env` was ever committed** — Run `git log --all -- .env` to confirm. If it appears in history, change your NLearn password and use `git filter-repo` to purge the history.

- **Consider encrypting `cookies.json`** — The session cookie is equivalent to your password for the duration of the session. If you're on a shared machine, encrypt it at rest using `cryptography` (Fernet) with a key derived from an env var.

---

## Performance

- **Cache active course IDs** — Both `get_deadlines` and `get_past_events` independently fetch active courses via an AJAX call. This is a redundant round-trip. Cache the result in-memory (or in a small JSON file with a TTL) and reuse across calls within the same session.

- **Parallelize PDF downloads** — If an assignment has multiple PDF attachments, they're downloaded sequentially. Use `asyncio` + `httpx.AsyncClient` or `concurrent.futures.ThreadPoolExecutor` to parallelize downloads.

---

## Testing

- **No tests exist** — There are zero test files in the project. At minimum, add:
  - A mock-based unit test for `parse_pdf_content` (inject sample bytes)
  - A unit test for `get_deadlines_for_sync` that mocks `get_deadlines` and checks ISO date formatting
  - An integration test for `get_session` that can be run manually against the live server

- **Add a `__main__` block to `server.py`** — It exists ✅ but there's no `--dry-run` or `--test` flag. Consider adding a `--test` mode that calls each tool once and prints results without starting the MCP server, useful for CI-style validation.

---

## Documentation

- **No `README.md`** — The project has no readme. Add one with: setup instructions (`uv sync`, `.env` setup, running the server), how to connect it to Claude Desktop (`claude_desktop_config.json` snippet), and a brief description of each MCP tool.

- **Add a `.env.example`** — The `.env` file is gitignored (good) but there's no `.env.example` showing the required variables. Anyone setting up the project fresh won't know what to configure.

- **Document the Moodle AJAX API endpoints used** — The `lib/ajax/service.php` calls are non-obvious. Add a comment block in `timeline.py` explaining what each AJAX method does and linking to Moodle docs, so future-you remembers why it works.
