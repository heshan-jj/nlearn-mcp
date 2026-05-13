# nlearn-mcp

MCP server for integrating your NLearn / Moodle account with Claude (via FastMCP).

## What it does

- Authenticates to Moodle using username/password and a cached cookie jar (`auth/cookies.json`).
- Scrapes your course timeline via Moodle AJAX endpoints to produce:
  - upcoming deadlines
  - past/missed deadlines
  - calendar-ready sync items
- Fetches assignment PDFs and extracts their text.
- Provides an on-demand `refresh_session` tool if your cookie session expires mid-day.

## Setup

1. Install Python 3.10+.
2. Copy `.env.example` to `.env` and fill in values.
3. Install dependencies:
   - Using `uv` (recommended if you have it):
     - `uv sync`
   - Or with pip:
     - `pip install -e .`
4. Start the MCP server:
   - `python server.py`

## Environment variables

See `.env.example` for required variables.

## Connect to Claude Desktop

Create/adjust your `claude_desktop_config.json` to start the MCP server process.
Example:

```json
{
  "mcpServers": {
    "nlearn-mcp": {
      "command": "python",
      "args": ["server.py"]
    }
  }
}
```

If your OS requires passing env vars explicitly to the process, set them in your launcher
environment or extend the config with an `env` block (shape depends on your Claude Desktop version).

## MCP tools

### `get_upcoming_deadlines(days: number = 14)`

Returns structured data:

```json
{
  "window_days": 14,
  "count": 3,
  "has_deadlines": true,
  "deadlines": [
    {
      "id": 123,
      "name": "Homework 1",
      "course_name": "CS101",
      "due_date_unix": 1750000000,
      "due_date_iso": "2026-05-20T12:00:00",
      "url": "https://.../pluginfile.php/.../some.pdf",
      "action_name": "Turn in",
      "action_url": null
    }
  ]
}
```

### `get_past_deadlines(days: number = 60)`

Same shape as `get_upcoming_deadlines`, but pulls actions from the past window.

### `get_deadlines_for_sync(days: number = 14)`

Returns a list of calendar-ready items (suitable for Claude to sync into Google Calendar):

```json
[
  {
    "title": "CS101 - Homework 1",
    "due_date": "2026-05-20T12:00:00",
    "course": "CS101",
    "description": "Course: CS101\nTask: Homework 1\nSubmit via NLearn. Link: https://...",
    "reminder_minutes": 1440
  }
]
```

### `get_assignment(assignment_url: string)`

Downloads the assignment page, finds PDF attachments, extracts their text, and returns the
combined extracted text as a string.

Important: the URL is validated to belong to your configured `NLEARN_URL` to reduce SSRF risk.

### `refresh_session()`

Clears the cached cookies (`auth/cookies.json`) and forces a new login on next request.
Useful if your session expires while Claude is running.

## Debug artifacts

When scraping fails to find expected HTML/data (e.g., missing `sesskey` or no PDF links),
the scrapers save debug HTML snippets into a temporary directory:

- `Temp/debug/` (system temp path; on Windows this is typically under `%TEMP%`)

