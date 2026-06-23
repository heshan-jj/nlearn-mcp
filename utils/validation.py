MIN_DAYS = 1
MAX_DAYS = 365


def validate_days(days: int) -> int:
    """Validate a deadline lookahead/lookback window supplied to an MCP tool."""
    if isinstance(days, bool) or not isinstance(days, int):
        raise ValueError("days must be an integer")

    if days < MIN_DAYS or days > MAX_DAYS:
        raise ValueError(f"days must be between {MIN_DAYS} and {MAX_DAYS}")

    return days
