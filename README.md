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

## 🔌 Connect to Claude

### Claude Desktop — install the `.mcpb` extension (recommended)

The `.mcpb` file is a one-click Claude Desktop extension (like the filesystem connector). Claude Code does **not** install `.mcpb` files directly — use the [Claude Code](#claude-code) section below instead.

#### Build the extension

```bash
npm install -g @anthropic-ai/mcpb
mcpb pack . nlearn-mcp.mcpb
```

#### Install

1. Double-click `nlearn-mcp.mcpb`, or drag it into the Claude Desktop window
2. Or: **Settings → Extensions → Advanced settings → Install Extension…**
3. Enter your **NLearn URL**, **username**, and **password** in the install dialog
4. Restart Claude Desktop if prompted

The extension uses the **uv** runtime — Claude Desktop manages Python and dependencies automatically.

---

### Claude Code

Claude Code uses the `claude mcp` CLI or a project `.mcp.json` file, not `.mcpb` bundles. Pick one of the options below.

#### Option A: `claude mcp add` (quickest)

From the project directory, register a local stdio server. Replace the credential values with your own:

```bash
claude mcp add --scope project nlearn-mcp \
  -e NLEARN_URL=https://nlearn.nsbm.ac.lk \
  -e NLEARN_USERNAME=your_username \
  -e NLEARN_PASSWORD=your_password \
  -- uv run --directory . server.py
```

On Windows PowerShell:

```powershell
claude mcp add --scope project nlearn-mcp `
  -e NLEARN_URL=https://nlearn.nsbm.ac.lk `
  -e NLEARN_USERNAME=your_username `
  -e NLEARN_PASSWORD=your_password `
  -- uv run --directory . server.py
```

If you don't have `uv`, use Python instead (dependencies must already be installed with `pip install -e .`):

```powershell
claude mcp add --scope project nlearn-mcp `
  -e NLEARN_URL=https://nlearn.nsbm.ac.lk `
  -e NLEARN_USERNAME=your_username `
  -e NLEARN_PASSWORD=your_password `
  -- python server.py
```

Verify and use:

```bash
claude mcp list          # check connection status
claude                   # start a session
/mcp                     # manage servers inside a session
```

#### Option B: project `.mcp.json` (share with teammates)

Create `.mcp.json` in the project root. **Do not commit real passwords** — each developer fills in credentials locally or uses environment variables on their machine:

```json
{
  "mcpServers": {
    "nlearn-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "server.py"],
      "env": {
        "NLEARN_URL": "https://nlearn.nsbm.ac.lk",
        "NLEARN_USERNAME": "your_username",
        "NLEARN_PASSWORD": "your_password"
      }
    }
  }
}
```

Start Claude Code in this project and approve the server when prompted. Run `/mcp` to confirm it shows as connected.

#### Option C: import from Claude Desktop

If you already installed `nlearn-mcp.mcpb` in Claude Desktop (macOS or WSL on Windows):

```bash
claude mcp add-from-claude-desktop
```

Select **nlearn-mcp** from the interactive list. Credentials configured during the Desktop install are reused.

---

### Manual `claude_desktop_config.json` (legacy)

If you prefer editing JSON instead of using the `.mcpb` installer, add this at the **root** of `claude_desktop_config.json` (sibling to `preferences`, **not** inside `epitaxyPrefs`):

```json
{
  "mcpServers": {
    "nlearn-mcp": {
      "command": "C:\\Users\\YOU\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": ["D:\\Projects\\nlearn-mcp\\server.py"],
      "cwd": "D:\\Projects\\nlearn-mcp"
    }
  }
}
```

Restart Claude Desktop after saving. Your `.env` file supplies credentials when using this approach.

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

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) to learn how to run tests, format code, and submit Pull Requests.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
