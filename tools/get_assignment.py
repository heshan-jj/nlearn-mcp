from scrapers.assignments import fetch_assignment_pdf_text
from auth.session import get_base_url
from urllib.parse import urlsplit


def _url_belongs_to_instance(url: str, base_url: str) -> bool:
    """
    Validate that `url` points to the same scheme+host (+port if explicit)
    as `base_url`, preventing SSRF via prompt injection.
    """
    parsed = urlsplit(url)
    base = urlsplit(base_url)

    # Require absolute URL
    if not parsed.scheme or not parsed.netloc:
        return False

    if parsed.scheme.lower() != base.scheme.lower():
        return False

    if (parsed.hostname or "").lower() != (base.hostname or "").lower():
        return False

    # Port check: if the base URL didn't specify a port, allow the default
    # implied by the scheme. If it did specify, require an exact match.
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


def get_assignment(assignment_url: str) -> str:
    """
    Downloads and extracts text from PDF attachments found on the given Moodle assignment page.
    
    Args:
        assignment_url (str): The direct URL to the assignment page (e.g., https://moodle.example.edu/mod/assign/view.php?id=...)
        
    Returns:
        str: The raw text extracted from the assignment brief PDF, preserving formatting as much as possible.
    """
    base_url = get_base_url()
    url = assignment_url.strip()
    if not _url_belongs_to_instance(url, base_url):
        return "Error: URL must belong to the configured NLearn instance."
    return fetch_assignment_pdf_text(url)
