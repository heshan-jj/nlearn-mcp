from urllib.parse import urlsplit


def url_belongs_to_instance(url: str, base_url: str) -> bool:
    """
    Validate that `url` points to the same scheme+host (+port if explicit)
    as `base_url`, preventing SSRF via prompt injection.
    """
    parsed = urlsplit(url)
    base = urlsplit(base_url)

    # Require absolute URL.
    if not parsed.scheme or not parsed.netloc:
        return False

    if parsed.scheme.lower() != base.scheme.lower():
        return False

    if (parsed.hostname or "").lower() != (base.hostname or "").lower():
        return False

    # If the base URL has no explicit port, allow only the scheme default.
    if base.port is not None:
        if parsed.port != base.port:
            return False
    else:
        default_port = 443 if base.scheme.lower() == "https" else 80
        if parsed.port is not None and parsed.port != default_port:
            return False

    # If the base URL includes a path prefix, enforce it.
    base_path = (base.path or "").rstrip("/")
    if base_path and not parsed.path.startswith(base_path):
        return False

    return True
