import logging
import os
import re
import tempfile
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

DEBUG_DIR = Path(tempfile.gettempdir()) / "nlearn-mcp-debug"

_TOKEN_PATTERNS = [
    re.compile(r'("sesskey"\s*:\s*")[^"]+(")', re.IGNORECASE),
    re.compile(r'(name=["\']sesskey["\']\s+value=["\'])[^"\']+(["\'])', re.IGNORECASE),
    re.compile(r'(MoodleSession=)[^;\s]+', re.IGNORECASE),
]


def _debug_artifacts_enabled() -> bool:
    return os.environ.get("NLEARN_DEBUG_ARTIFACTS") == "1"


def _redact_sensitive_values(text: str) -> str:
    redacted = text
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub(r"\1<redacted>\2", redacted)
    return redacted


def save_debug_text(context: str, text: str, *, max_chars: int = 200_000) -> None:
    """Save redacted scraper debug output only when explicitly enabled."""
    if not _debug_artifacts_enabled():
        logger.info("Debug artifact skipped for %s; set NLEARN_DEBUG_ARTIFACTS=1 to enable.", context)
        return

    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        fname = f"{context}_{int(time.time())}_{uuid.uuid4().hex}.html"
        path = DEBUG_DIR / fname
        path.write_text(_redact_sensitive_values(text[:max_chars]), encoding="utf-8", errors="replace")
        logger.info("Saved debug artifact: %s", path)
    except Exception as e:
        logger.warning("Failed to save debug artifact (%s): %s", context, e)
