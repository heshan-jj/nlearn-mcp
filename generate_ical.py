"""
generate_ical.py
----------------
Fetches upcoming NLearn/Moodle deadlines and writes them to `deadlines.ics`
in iCalendar format. Intended to be run by the GitHub Action on a schedule.

Usage:
    python generate_ical.py [--days 30] [--output deadlines.ics]
"""

import argparse
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _to_ical_dt(unix_ts: int) -> str:
    """Convert a Unix timestamp to iCal UTC datetime string (YYYYMMDDTHHMMSSZ)."""
    dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _now_ical() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    """Escape special characters for iCal text fields."""
    return (
        text.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """
    iCal line folding: lines longer than 75 octets must be split.
    Continuation lines begin with a single whitespace character.
    """
    MAX = 75
    if len(line.encode("utf-8")) <= MAX:
        return line

    chunks = []
    current = ""
    for char in line:
        candidate = current + char
        if len(candidate.encode("utf-8")) > MAX:
            chunks.append(current)
            current = " " + char  # folded continuation
            MAX = 74  # continuation lines are one char shorter
        else:
            current = candidate
    if current:
        chunks.append(current)

    return "\r\n".join(chunks)


def build_ical(deadlines, days: int) -> str:
    """Build a full iCal string from a list of Deadline dataclass instances."""
    now = _now_ical()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//nlearn-mcp//NLearn Sentinel//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:NLearn Deadlines ({days}d)",
        "X-WR-TIMEZONE:UTC",
        "X-WR-CALDESC:Upcoming assignment deadlines from NLearn/Moodle",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ]

    for d in deadlines:
        uid = f"nlearn-{d.id}@nlearn-mcp"
        dt_due = _to_ical_dt(d.due_date)
        action_link = d.action_url if d.action_url else d.url
        summary = _escape(f"{d.course_name} – {d.name}")
        description = _escape(
            f"Course: {d.course_name}\n"
            f"Task: {d.name}\n"
            f"Action: {d.action_name or 'Submit'}\n"
            f"Link: {action_link}"
        )

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{dt_due}",
            f"DTEND:{dt_due}",        # point-in-time event (due date = start = end)
            _fold(f"SUMMARY:{summary}"),
            _fold(f"DESCRIPTION:{description}"),
            _fold(f"URL:{action_link}"),
            # 24-hour reminder alarm
            "BEGIN:VALARM",
            "TRIGGER:-PT24H",
            "ACTION:DISPLAY",
            _fold(f"DESCRIPTION:Due tomorrow: {summary}"),
            "END:VALARM",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    # iCal spec requires CRLF line endings
    return "\r\n".join(lines) + "\r\n"


def main():
    parser = argparse.ArgumentParser(description="Generate iCal feed from NLearn deadlines")
    parser.add_argument("--days", type=int, default=30, help="Look-ahead window in days (default: 30)")
    parser.add_argument("--output", type=str, default="deadlines.ics", help="Output file path (default: deadlines.ics)")
    args = parser.parse_args()

    logger.info(f"Fetching deadlines for the next {args.days} days...")

    from scrapers.timeline import get_deadlines
    deadlines = get_deadlines(days=args.days)

    logger.info(f"Found {len(deadlines)} deadline(s).")

    ical_content = build_ical(deadlines, days=args.days)

    output_path = Path(args.output)
    output_path.write_text(ical_content, encoding="utf-8")
    logger.info(f"Written to {output_path.resolve()}")

    # Print a summary
    for d in deadlines:
        due = time.strftime("%Y-%m-%d %H:%M", time.localtime(d.due_date))
        print(f"  [{due}] {d.course_name}: {d.name}")


if __name__ == "__main__":
    main()
