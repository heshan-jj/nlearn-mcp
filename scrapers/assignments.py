import logging
from urllib.parse import unquote, urljoin, urlsplit
from bs4 import BeautifulSoup

from auth.session import get_base_url, session_scope
from utils.debug import save_debug_text
from utils.pdf_parser import parse_pdf_content
from utils.url_validation import url_belongs_to_instance

logger = logging.getLogger(__name__)

MAX_PDF_BYTES = 20 * 1024 * 1024


def _pdf_filename(pdf_url: str) -> str:
    filename = unquote(urlsplit(pdf_url).path.rstrip("/").split("/")[-1])
    return filename or "assignment.pdf"


def _discover_pdf_links(html: str, assignment_url: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    pdf_links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        resolved_url = urljoin(assignment_url, href)
        base_href = urlsplit(resolved_url).path.lower()
        if not base_href.endswith(".pdf"):
            continue

        if not url_belongs_to_instance(resolved_url, base_url):
            logger.warning("Skipping off-instance PDF attachment: %s", resolved_url)
            continue

        if resolved_url not in pdf_links:
            pdf_links.append(resolved_url)

    return pdf_links

def fetch_assignment_pdf_text(assignment_url: str) -> str:
    """
    Navigates to the given Moodle assignment URL, finds attached PDF files,
    downloads them, and extracts their text.
    """
    with session_scope() as client:
        base_url = get_base_url()
        
        logger.info(f"Fetching assignment page: {assignment_url}")
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
        
        pdf_links = _discover_pdf_links(response.text, assignment_url, base_url)
                    
        if not pdf_links:
            # Some assignment attachments might be embedded differently, but usually they are <a> tags.
            logger.error(
                "No PDF attachments found (first 2000 chars): %s",
                response.text[:2000],
            )
            save_debug_text("assignment_no_pdfs_found", response.text)
            return "No PDF attachments found on the assignment page. The assignment brief might be directly in the HTML or in a different format."
            
        results = []
        for pdf_url in pdf_links:
            logger.info(f"Found PDF attachment: {pdf_url}")
            
            try:
                pdf_response = client.get(pdf_url)
                pdf_response.raise_for_status()

                if len(pdf_response.content) > MAX_PDF_BYTES:
                    results.append(
                        f"Skipped {_pdf_filename(pdf_url)}: PDF is larger than {MAX_PDF_BYTES // (1024 * 1024)} MB."
                    )
                    continue

                logger.info(f"Downloaded PDF, size: {len(pdf_response.content)} bytes. Extracting text...")
                extracted_text = parse_pdf_content(pdf_response.content)
                
                results.append(f"--- Document: {_pdf_filename(pdf_url)} ---\n{extracted_text}")
            except Exception as e:
                logger.error(f"Failed to process PDF {pdf_url}: {e}")
                results.append(f"Failed to process {pdf_url}: {e}")
                
        return "\n\n==== NEXT ATTACHMENT ====\n\n".join(results)
