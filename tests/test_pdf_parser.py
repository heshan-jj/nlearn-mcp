import unittest
from unittest.mock import MagicMock, patch

from utils.pdf_parser import parse_pdf_content


class TestParsePdfContent(unittest.TestCase):
    def test_parse_pdf_content_concatenates_pages(self) -> None:
        # Fake pdfplumber API: `open(...).pages` and `page.extract_text(layout=True)`.
        class FakePage:
            def __init__(self, text: str) -> None:
                self._text = text

            def extract_text(self, layout: bool = True) -> str:
                return self._text

        fake_pdf = MagicMock()
        fake_pdf.pages = [FakePage("Page 1 text"), FakePage("Page 2 text")]

        fake_ctx = MagicMock()
        fake_ctx.__enter__.return_value = fake_pdf
        fake_ctx.__exit__.return_value = False

        with patch("utils.pdf_parser.pdfplumber.open", return_value=fake_ctx):
            out = parse_pdf_content(b"%PDF-1.4 fake bytes")

        self.assertIn("Page 1 text", out)
        self.assertIn("Page 2 text", out)
        self.assertIn("\n--- PAGE BREAK ---\n", out)

    def test_parse_pdf_content_handles_exceptions(self) -> None:
        with patch("utils.pdf_parser.pdfplumber.open", side_effect=RuntimeError("boom")):
            out = parse_pdf_content(b"%PDF-1.4 fake bytes")

        self.assertTrue(out.startswith("Error extracting text from PDF:"))


if __name__ == "__main__":
    unittest.main()

