from scrapers.assignments import fetch_assignment_pdf_text
from auth.session import get_base_url
from utils.url_validation import url_belongs_to_instance


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
    if not url_belongs_to_instance(url, base_url):
        return "Error: URL must belong to the configured NLearn instance."
    return fetch_assignment_pdf_text(url)
