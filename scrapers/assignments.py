import logging
from bs4 import BeautifulSoup
from typing import Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from auth.session import get_session, get_base_url
from utils.pdf_parser import parse_pdf_content

logger = logging.getLogger(__name__)

def fetch_assignment_pdf_text(assignment_url: str) -> str:
    """
    Navigates to the given Moodle assignment URL, finds attached PDF files,
    downloads them, and extracts their text.
    """
    client = get_session()
    
    logger.info(f"Fetching assignment page: {assignment_url}")
    response = client.get(assignment_url)
    try:
        response.raise_for_status()
    except Exception as e:
        return f"Failed to fetch assignment page: {e}"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    pdf_links = []
    
    # Search for PDF links
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Moodle attachment URLs often look like:
        # https://moodle.../pluginfile.php/.../something.pdf
        # https://moodle.../pluginfile.php/.../something.pdf?forcedownload=1
        base_href = href.split('?')[0].lower()
        if base_href.endswith('.pdf'):
            if href not in pdf_links:
                pdf_links.append(href)
                
    if not pdf_links:
        # Some assignment attachments might be embedded differently, but usually they are <a> tags.
        return "No PDF attachments found on the assignment page. The assignment brief might be directly in the HTML or in a different format."
        
    results = []
    for pdf_url in pdf_links:
        logger.info(f"Found PDF attachment: {pdf_url}")
        
        try:
            pdf_response = client.get(pdf_url)
            pdf_response.raise_for_status()
            
            logger.info(f"Downloaded PDF, size: {len(pdf_response.content)} bytes. Extracting text...")
            extracted_text = parse_pdf_content(pdf_response.content)
            
            results.append(f"--- Document: {pdf_url.split('/')[-1].split('?')[0]} ---\n{extracted_text}")
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_url}: {e}")
            results.append(f"Failed to process {pdf_url}: {e}")
            
    return "\n\n==== NEXT ATTACHMENT ====\n\n".join(results)
