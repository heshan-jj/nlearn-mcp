# NLearn MCP (NLearn Sentinel)

[![Python Tests](https://github.com/heshan-jj/nlearn-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/heshan-jj/nlearn-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

An Model Context Protocol (MCP) server for integrating your Moodle-based academic dashboard (NLearn) with Claude and other LLM clients. Built on [FastMCP](https://github.com/modelcontextprotocol/python-sdk).

---

## ✨ Features

- **Automated Authentication**: Seamless login to Moodle using credentials and secure, cached cookie jars (`auth/cookies.json`).
- **Timeline Scraping**: Scrapes Moodle's internal AJAX endpoints to fetch upcoming and past deadlines without requiring a native Moodle REST API token.
- **PDF Brief Extraction**: Automatically downloads course/assignment brief PDFs and extracts their text layouts, making assignment details instantly available to Claude.
- **Google Calendar Ready**: Special tool formatting that outputs structured events ready for Claude to insert into your Google Calendar.
- **On-demand Refresh**: Dedicated `refresh_session` tool to re-authenticate on the fly if a session expires during use.
- **Local iCal Sync Feed**: Export deadlines to an `.ics` file locally, ready for hosting/publishing.

---

## 🔒 Security & Safe-to-Run Guarantees

When using AI agents like Claude to navigate web pages, security is paramount. NLearn MCP implements:
- **SSRF / Prompt Injection Protection**: The `get_assignment` tool parses and strictly validates any input URL before performing HTTP requests. It restricts requests to the hostname configured in your `.env` (`NLEARN_URL`), preventing malicious instructions from causing Server-Side Request Forgery.
- **Credential Safety**: Session cookies are stored locally in the `auth` directory. The project is pre-configured with a `.gitignore` to prevent committing your password or cookies to source control.

---

## 🚀 Setup

### 1. Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`

### 2. Install & Configure

Clone the repository and copy the environment template:
```bash
git clone https://github.com/heshan-jj/nlearn-mcp.git
cd nlearn-mcp
cp .env.example .env
```

Open `.env` and fill in your details:
```env
NLEARN_URL="https://nlearn.nsbm.ac.lk"
NLEARN_USERNAME="your_username"
NLEARN_PASSWORD="your_password"
```

> **Note**: If your NLearn instance uses complex SSO (Single Sign-On) or blocks automated logins, you might need to manually configure `auth/cookies.json`. To do this, copy your active browser session cookies (such as `MoodleSession` and `MOODLEID1_`) and save them as a JSON object in `auth/cookies.json`.

### 3. Install Dependencies

#### Using `uv` (Recommended):
```bash
uv sync
```

#### Using `pip`:
```bash
pip install -e .
```

---

## 🔌 Connection to Claude Desktop

Add `nlearn-mcp` to your `claude_desktop_config.json` configuration file:

```json
{
  "mcpServers": {
    "nlearn-mcp": {
      "command": "python",
      "args": ["/path/to/nlearn-mcp/server.py"]
    }
  }
}
```

*Note: Replace `/path/to/nlearn-mcp/` with the absolute path of your local clone. On Windows, make sure to escape backslashes or use quotes appropriately.*

---

## 🛠️ MCP Tools Exposed

### 📅 `get_upcoming_deadlines(days: int = 14)`
Returns upcoming academic tasks:
```json
{
  "window_days": 14,
  "count": 3,
  "has_deadlines": true,
  "deadlines": [
    {
      "id": 12345,
      "name": "Midterm Assignment Submission",
      "course_name": "CS301 - Advanced Algorithms",
      "due_date_unix": 1750000000,
      "due_date_iso": "2026-05-20T12:00:00Z",
      "url": "https://moodle.your-university.edu/mod/assign/view.php?id=123",
      "action_name": "Add submission",
      "action_url": "https://moodle.your-university.edu/mod/assign/view.php?id=123&action=editsubmission"
    }
  ]
}
```

### 🗓️ `get_past_deadlines(days: int = 60)`
Same structured shape as `get_upcoming_deadlines`, but pulls calendar activities from the past window.

### 🔄 `get_deadlines_for_sync(days: int = 14)`
Returns a calendar-ready array optimized for Claude to interact with Google Calendar:
```json
[
  {
    "title": "CS301 - Midterm Assignment Submission",
    "due_date": "2026-05-20T12:00:00Z",
    "course": "CS301 - Advanced Algorithms",
    "description": "Course: CS301 - Advanced Algorithms\nTask: Midterm Assignment Submission\nSubmit via NLearn. Link: https://...",
    "reminder_minutes": 1440
  }
]
```

### 📄 `get_assignment(assignment_url: str)`
Downloads the Moodle assignment page, detects PDF attachment briefs, and returns the extracted text layout.
*Enforces base URL validation check to prevent SSRF.*

### 🔑 `refresh_session()`
Deletes cached cookies (`auth/cookies.json`) and forces a new login on the next execution.

---

## 🛠️ Calendar Generation (Local iCal Feed)

If you wish to export a live iCal calendar feed:
1. Run the local generation script:
   ```bash
   python generate_ical.py --days 30 --output deadlines.ics
   ```
2. For Windows users, a portable scheduler helper is provided in `run_ical.bat`. Run this periodically (e.g. via Windows Task Scheduler) to automatically update `deadlines.ics` and push updates to your personal repo, letting GitHub Pages host the live iCal link for Google Calendar/Outlook.

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) to learn how to run tests, format code, and submit Pull Requests.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
