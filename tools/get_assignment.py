from scrapers.assignments import fetch_assignment_pdf_text

def get_assignment(assignment_url: str) -> str:
    """
    Downloads and extracts text from PDF attachments found on the given Moodle assignment page.
    
    Args:
        assignment_url (str): The direct URL to the assignment page (e.g., https://moodle.example.edu/mod/assign/view.php?id=...)
        
    Returns:
        str: The raw text extracted from the assignment brief PDF, preserving formatting as much as possible.
    """
    return fetch_assignment_pdf_text(assignment_url)
