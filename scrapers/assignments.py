import logging
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from auth.session import get_base_url, session_scope
from utils.debug import save_debug_text
from utils.pdf_parser import parse_pdf_content
from utils.docx_parser import parse_docx_content
from utils.pptx_parser import parse_pptx_content
from utils.url_validation import url_belongs_to_instance

logger = logging.getLogger(__name__)

MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
MAX_LINKED_RESOURCES = 5

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx")

RESOURCE_PATH_FRAGMENT = "/mod/resource/view.php"


def _attachment_filename(url: str) -> str:
    filename = unquote(urlsplit(url).path.rstrip("/").split("/")[-1])
    return filename or "attachment"


def _file_extension(url: str) -> str:
    path = urlsplit(url).path.lower()
    for ext in SUPPORTED_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return ""


def _add_unique_url(urls: list[str], url: str) -> None:
    if url not in urls:
        urls.append(url)


def _discover_attachment_links(html: str, page_url: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        resolved_url = urljoin(page_url, href)

        if not _file_extension(resolved_url):
            continue

        if not url_belongs_to_instance(resolved_url, base_url):
            logger.warning("Skipping off-instance attachment: %s", resolved_url)
            continue

        _add_unique_url(links, resolved_url)

    return links


def _discover_linked_resource_urls(html: str, page_url: str, base_url: str) -> list[str]:
    """
    Find Moodle file-resource activity links on an assignment page, including
    previous/next activity navigation and links in the main content area.
    """
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    def maybe_add(href: str | None) -> None:
        if not href:
            return
        resolved = urljoin(page_url, href)
        if RESOURCE_PATH_FRAGMENT not in resolved:
            return
        if not url_belongs_to_instance(resolved, base_url):
            logger.warning("Skipping off-instance linked resource: %s", resolved)
            return
        _add_unique_url(links, resolved)

    for link_id in ("prev-activity-link", "next-activity-link"):
        el = soup.find(id=link_id)
        if el:
            maybe_add(el.get("href"))

    main = soup.find(id="region-main") or soup.find(role="main") or soup
    for a in main.find_all("a", href=True):
        maybe_add(a["href"])

    intro = soup.find(id="intro")
    if intro:
        for a in intro.find_all("a", href=True):
            maybe_add(a["href"])

    return links[:MAX_LINKED_RESOURCES]


def _resolve_resource_attachment_urls(client, resource_url: str, base_url: str) -> list[str]:
    """
    Follow a Moodle resource activity URL. File resources redirect to pluginfile.php;
    other resource pages may still contain direct attachment links in HTML.
    """
    logger.info("Following linked resource: %s", resource_url)
    response = client.get(resource_url, follow_redirects=True)
    response.raise_for_status()

    final_url = str(response.url)
    if _file_extension(final_url) and url_belongs_to_instance(final_url, base_url):
        return [final_url]

    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        return _discover_attachment_links(response.text, resource_url, base_url)

    return []


def _collect_attachment_urls(client, html: str, page_url: str, base_url: str) -> list[str]:
    attachment_links = _discover_attachment_links(html, page_url, base_url)

    for resource_url in _discover_linked_resource_urls(html, page_url, base_url):
        try:
            for file_url in _resolve_resource_attachment_urls(client, resource_url, base_url):
                _add_unique_url(attachment_links, file_url)
        except Exception as e:
            logger.error("Failed to resolve linked resource %s: %s", resource_url, e)

    return attachment_links


def _parse_attachment(content: bytes, ext: str, filename: str) -> str:
    if ext == ".pdf":
        return parse_pdf_content(content)
    if ext == ".docx":
        return parse_docx_content(content)
    if ext == ".pptx":
        return parse_pptx_content(content)
    return f"Unsupported attachment format: {filename}"


def _download_and_extract(client, url: str) -> str:
    ext = _file_extension(url)
    filename = _attachment_filename(url)
    logger.info("Found attachment: %s (%s)", filename, ext)

    file_response = client.get(url)
    file_response.raise_for_status()

    if len(file_response.content) > MAX_ATTACHMENT_BYTES:
        return (
            f"Skipped {filename}: file is larger than "
            f"{MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB."
        )

    logger.info(
        "Downloaded %s, size: %d bytes. Extracting text...",
        filename,
        len(file_response.content),
    )
    extracted_text = _parse_attachment(file_response.content, ext, filename)
    return f"--- Document: {filename} ---\n{extracted_text}"


def _extract_intro_text(html: str) -> str:
    """Extract assignment description text from the Moodle intro/description block."""
    soup = BeautifulSoup(html, "html.parser")
    intro = soup.find(id="intro") or soup.find(class_="activity-description")
    if not intro:
        return ""

    text = intro.get_text("\n", strip=True)
    return text.strip()


def fetch_assignment_text(assignment_url: str) -> str:
    """
    Navigates to the given Moodle assignment URL, finds attached PDF, DOCX, and
    PPTX files (including linked Moodle resource activities), downloads them,
    and extracts their text.
    """
    with session_scope() as client:
        base_url = get_base_url()

        logger.info("Fetching assignment page: %s", assignment_url)
        response = client.get(assignment_url)
        try:
            response.raise_for_status()
        except Exception as e:
            logger.error(
                "Failed fetching assignment page (first 2000 chars): %s",
                getattr(response, "text", "")[:2000],
            )
            save_debug_text("assignment_page_fetch_failed", getattr(response, "text", ""))
            return f"Failed to fetch assignment page: {e}"

        attachment_links = _collect_attachment_urls(
            client, response.text, assignment_url, base_url
        )

        if not attachment_links:
            intro_text = _extract_intro_text(response.text)
            if intro_text:
                logger.info("No file attachments; returning assignment intro text from page HTML.")
                return f"--- Assignment Instructions (from page) ---\n{intro_text}"

            logger.error(
                "No supported attachments found (first 2000 chars): %s",
                response.text[:2000],
            )
            save_debug_text("assignment_no_attachments_found", response.text)
            return (
                "No supported attachments found on the assignment page "
                "(expected .pdf, .docx, or .pptx). "
                "The assignment brief might be directly in the page HTML or in a different format."
            )

        results = []
        for url in attachment_links:
            try:
                results.append(_download_and_extract(client, url))
            except Exception as e:
                filename = _attachment_filename(url)
                logger.error("Failed to process attachment %s: %s", url, e)
                results.append(f"Failed to process {filename}: {e}")

        return "\n\n==== NEXT ATTACHMENT ====\n\n".join(results)


# Keep the old name as an alias so any existing callers don't break.
fetch_assignment_pdf_text = fetch_assignment_text
