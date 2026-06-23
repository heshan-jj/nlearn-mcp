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

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx")


def _attachment_filename(url: str) -> str:
    filename = unquote(urlsplit(url).path.rstrip("/").split("/")[-1])
    return filename or "attachment"


def _file_extension(url: str) -> str:
    path = urlsplit(url).path.lower()
    for ext in SUPPORTED_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return ""


def _discover_attachment_links(html: str, assignment_url: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        resolved_url = urljoin(assignment_url, href)

        if not _file_extension(resolved_url):
            continue

        if not url_belongs_to_instance(resolved_url, base_url):
            logger.warning("Skipping off-instance attachment: %s", resolved_url)
            continue

        if resolved_url not in links:
            links.append(resolved_url)

    return links


def _parse_attachment(content: bytes, ext: str, filename: str) -> str:
    if ext == ".pdf":
        return parse_pdf_content(content)
    if ext == ".docx":
        return parse_docx_content(content)
    if ext == ".pptx":
        return parse_pptx_content(content)
    return f"Unsupported attachment format: {filename}"


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
    PPTX files, downloads them, and extracts their text.
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

        attachment_links = _discover_attachment_links(response.text, assignment_url, base_url)

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
            ext = _file_extension(url)
            filename = _attachment_filename(url)
            logger.info("Found attachment: %s (%s)", filename, ext)

            try:
                file_response = client.get(url)
                file_response.raise_for_status()

                if len(file_response.content) > MAX_ATTACHMENT_BYTES:
                    results.append(
                        f"Skipped {filename}: file is larger than "
                        f"{MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB."
                    )
                    continue

                logger.info(
                    "Downloaded %s, size: %d bytes. Extracting text...",
                    filename,
                    len(file_response.content),
                )
                extracted_text = _parse_attachment(file_response.content, ext, filename)
                results.append(f"--- Document: {filename} ---\n{extracted_text}")

            except Exception as e:
                logger.error("Failed to process attachment %s: %s", url, e)
                results.append(f"Failed to process {filename}: {e}")

        return "\n\n==== NEXT ATTACHMENT ====\n\n".join(results)


# Keep the old name as an alias so any existing callers don't break.
fetch_assignment_pdf_text = fetch_assignment_text
