import io
import pdfplumber
import logging

logger = logging.getLogger(__name__)

def parse_pdf_content(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF file preserving layout as much as possible.
    """
    text_pages = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                logger.info(f"Extracting text from page {i+1}/{len(pdf.pages)}...")
                text = page.extract_text(layout=True)
                if text:
                    text_pages.append(text)
        return "\n--- PAGE BREAK ---\n".join(text_pages)
    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        return f"Error extracting text from PDF: {str(e)}"
