# NLearn MCP (NLearn Sentinel)

[![Python Tests](https://github.com/heshan-jj/nlearn-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/heshan-jj/nlearn-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

Connect Claude to your NLearn / Moodle dashboard — deadlines, assignment briefs, and calendar-ready events. Built on [FastMCP](https://github.com/modelcontextprotocol/python-sdk).

## Quick start (Claude Desktop)

The easiest way to use NLearn MCP is the `.mcpb` extension. No repo clone, no manual Python setup.

**Prerequisites:** [Claude Desktop](https://claude.ai/download) (v0.10+)

1. Download [`nlearn-mcp.mcpb`](https://github.com/heshan-jj/nlearn-mcp/releases/latest/download/nlearn-mcp.mcpb) from the latest GitHub release.
2. Double-click the file, or drag it into Claude Desktop.
   - Alternatively: **Settings → Extensions → Advanced settings → Install Extension…**
3. Enter your **NLearn URL**, **username**, and **password** when prompted.
4. Restart Claude Desktop if asked.

Your credentials stay on your machine. Claude Desktop handles Python and dependencies via the bundled `uv` runtime.

> **SSO or blocked logins:** If automated login fails, copy your browser session cookies (`MoodleSession`, `MOODLEID1_`, etc.) into `auth/cookies.json` in the extension install directory. See [manual cookie setup](#manual-cookie-setup) below.

## What it does

- Logs into NLearn and caches session cookies locally
- Fetches upcoming and past deadlines from Moodle's timeline
- Downloads assignment brief attachments (PDF, DOCX, PPTX) and extracts their text
- Formats deadlines for Google Calendar sync
- Re-authenticates on demand when sessions expire

## Tools

| Tool | Description |
|------|-------------|
| `get_upcoming_deadlines` | Upcoming tasks within a date window (default 14 days) |
| `get_past_deadlines` | Past/missed tasks within a date window (default 60 days) |
| `get_deadlines_for_sync` | Calendar-ready events for Google Calendar |
| `get_assignment` | Fetch and extract text from an assignment brief (PDF, DOCX, or PPTX) |
| `refresh_session` | Clear cached cookies and force a new login |

## Security

- **URL validation** — `get_assignment` only requests URLs on your configured NLearn host, blocking SSRF via prompt injection.
- **Local credentials** — Passwords and cookies are stored on your machine only. Never commit `.env` or `auth/cookies.json`.

## Other ways to connect

### Claude Code

Claude Code does not install `.mcpb` files. From a cloned repo:

```powershell
claude mcp add --scope project nlearn-mcp `
  -e NLEARN_URL=https://nlearn.nsbm.ac.lk `
  -e NLEARN_USERNAME=your_username `
  -e NLEARN_PASSWORD=your_password `
  -- uv run --directory . server.py
```

If you already installed the extension in Claude Desktop:

```bash
claude mcp add-from-claude-desktop
```

Run `/mcp` inside a session to confirm the server is connected.

### Run from source

For development or clients that use stdio MCP config directly.

**Prerequisites:** Python 3.10+, [uv](https://github.com/astral-sh/uv) (recommended) or `pip`

```bash
git clone https://github.com/heshan-jj/nlearn-mcp.git
cd nlearn-mcp
cp .env.example .env   # fill in your credentials
uv sync                # or: pip install -e .
```

Point your MCP client at `uv run server.py` (or `python server.py`) with `NLEARN_URL`, `NLEARN_USERNAME`, and `NLEARN_PASSWORD` set in the environment or `.env`.

### Manual cookie setup

If SSO blocks automated login, save active browser cookies as JSON in `auth/cookies.json`:

```json
{
  "MoodleSession": "your_session_value",
  "MOODLEID1_": "your_moodle_id_value"
}
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for tests, formatting, and pull request guidelines.

## License

MIT — see [LICENSE](LICENSE).
