# 📋 Audit Summary

> Audit Date: 2026-05-12
> Project: nlearn mcp

---

## Health Score: 7/10

Solid foundation. The architecture is well-thought-out, the Moodle AJAX API usage is smart, and the separation between scrapers/tools/auth is clean. The main concerns are a critical security issue with credentials, one crash-prone code path, and a missing dependency manifest — none of which are hard to fix.

---

## Tech Stack

- **Language:** Python 3.x
- **MCP Framework:** FastMCP (mcp.server.fastmcp)
- **HTTP Client:** httpx (sync)
- **HTML Parsing:** BeautifulSoup4
- **PDF Parsing:** pdfplumber
- **Auth:** Cookie-based session persistence (JSON)
- **Environment:** python-dotenv

---

## Project Stats

- Total files scanned: 9
- Directories: 5 (auth, scrapers, tools, utils, root)
- Critical fixes needed: **5**
- Non-critical fixes: **4**
- Improvements suggested: **12**

---

## Key Findings

The project successfully implements the full Phase 1–4 plan: session auth with cookie caching, Moodle AJAX timeline scraping, PDF extraction, and calendar-ready sync output. The MCP tool registration in `server.py` is clean and minimal. The sesskey extraction approach (scraping from dashboard HTML then calling `lib/ajax/service.php`) is the correct pattern for Moodle without a REST API token.

The biggest structural issue is code duplication — `get_deadlines` and `get_past_events` share ~40 lines of identical setup logic that should be extracted into shared helpers. The `sys.path` hacks in scrapers suggest the project isn't installed as a package, which can cause import issues in certain MCP server launch contexts.

---

## Risk Areas

1. **🔴 Credentials in `.env`** — Your actual NLearn password is in the `.env` file. Verify it has never been committed to git. This is the highest priority item.

2. **🟠 `get_past_events` crash bug** — The unsafeguarded `.group(1)` call on the sesskey regex will throw an `AttributeError` with no useful error message if the dashboard HTML changes or the session is stale. Fix before relying on `get_past_deadlines` in production.

3. **🟡 No dependency manifest** — Without a `pyproject.toml` or `requirements.txt`, the project is not reproducible. Add one so the MCP server can be reliably reinstalled if the environment breaks.
