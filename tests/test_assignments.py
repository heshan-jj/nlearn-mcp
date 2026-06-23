import unittest

from scrapers.assignments import _discover_attachment_links, _file_extension


class TestFileExtension(unittest.TestCase):
    def test_pdf_detected(self) -> None:
        self.assertEqual(_file_extension("https://example.edu/file.pdf"), ".pdf")

    def test_docx_detected(self) -> None:
        self.assertEqual(_file_extension("https://example.edu/brief.docx"), ".docx")

    def test_pptx_detected(self) -> None:
        self.assertEqual(_file_extension("https://example.edu/slides.pptx"), ".pptx")

    def test_query_string_ignored(self) -> None:
        self.assertEqual(
            _file_extension("https://example.edu/pluginfile.php/123/brief.docx?forcedownload=1"),
            ".docx",
        )

    def test_unsupported_extension_returns_empty(self) -> None:
        self.assertEqual(_file_extension("https://example.edu/image.png"), "")

    def test_doc_legacy_not_supported(self) -> None:
        self.assertEqual(_file_extension("https://example.edu/file.doc"), "")


class TestDiscoverAttachmentLinks(unittest.TestCase):
    def test_discovers_pdf_links(self) -> None:
        html = '<a href="/pluginfile.php/1/brief.pdf?forcedownload=1">Brief</a>'
        links = _discover_attachment_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )
        self.assertEqual(
            links,
            ["https://moodle.example.edu/pluginfile.php/1/brief.pdf?forcedownload=1"],
        )

    def test_discovers_docx_links(self) -> None:
        html = '<a href="/pluginfile.php/1/brief.docx">Brief</a>'
        links = _discover_attachment_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )
        self.assertEqual(
            links,
            ["https://moodle.example.edu/pluginfile.php/1/brief.docx"],
        )

    def test_discovers_pptx_links(self) -> None:
        html = '<a href="/pluginfile.php/1/slides.pptx">Slides</a>'
        links = _discover_attachment_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )
        self.assertEqual(
            links,
            ["https://moodle.example.edu/pluginfile.php/1/slides.pptx"],
        )

    def test_discovers_mixed_formats(self) -> None:
        html = """
        <a href="/pluginfile.php/1/brief.pdf">PDF</a>
        <a href="/pluginfile.php/2/slides.pptx">PPTX</a>
        <a href="/pluginfile.php/3/notes.docx">DOCX</a>
        """
        links = _discover_attachment_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )
        self.assertEqual(len(links), 3)
        self.assertTrue(any(".pdf" in l for l in links))
        self.assertTrue(any(".pptx" in l for l in links))
        self.assertTrue(any(".docx" in l for l in links))

    def test_deduplicates_links(self) -> None:
        html = """
        <a href="/pluginfile.php/1/brief.pdf">First</a>
        <a href="https://moodle.example.edu/pluginfile.php/1/brief.pdf">Duplicate</a>
        """
        links = _discover_attachment_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )
        self.assertEqual(len(links), 1)

    def test_skips_off_instance_urls(self) -> None:
        html = """
        <a href="https://evil.example/brief.pdf">External</a>
        <a href="/pluginfile.php/1/brief.pdf">Safe</a>
        """
        links = _discover_attachment_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )
        self.assertEqual(len(links), 1)
        self.assertIn("moodle.example.edu", links[0])

    def test_skips_unsupported_extensions(self) -> None:
        html = """
        <a href="/pluginfile.php/1/image.png">Image</a>
        <a href="/pluginfile.php/2/brief.pdf">Brief</a>
        """
        links = _discover_attachment_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )
        self.assertEqual(len(links), 1)
        self.assertIn(".pdf", links[0])

    def test_returns_empty_when_no_supported_links(self) -> None:
        html = '<a href="/pluginfile.php/1/image.png">Image</a>'
        links = _discover_attachment_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )
        self.assertEqual(links, [])


if __name__ == "__main__":
    unittest.main()
