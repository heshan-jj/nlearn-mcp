from __future__ import annotations

from auth.session import COOKIES_FILE, get_base_url, session_scope


def refresh_session() -> dict:
    """
    Clears the cached NLearn/Moodle cookies and re-authenticates on demand.
    """
    # Delete cached cookies so the next session scope forces a login flow.
    try:
        if COOKIES_FILE.exists():
            COOKIES_FILE.unlink()
    except Exception as e:
        # Don't fail hard; we'll attempt to re-auth anyway.
        return {"ok": False, "error": f"Failed to clear cookies cache: {e}"}

    # Force a fresh authenticated session by running a lightweight request.
    base_url = get_base_url()
    with session_scope() as client:
        resp = client.get(f"{base_url}/my/")
        resp.raise_for_status()

    return {"ok": True, "message": "Session refreshed (cookies cleared and re-authenticated)."}

