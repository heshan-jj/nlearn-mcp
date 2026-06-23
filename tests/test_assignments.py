import unittest

from scrapers.assignments import _discover_pdf_links


class TestAssignmentPdfDiscovery(unittest.TestCase):
    def test_discover_pdf_links_resolves_relative_urls(self) -> None:
        html = """
        <a href="/pluginfile.php/123/brief.pdf?forcedownload=1">Brief</a>
        <a href="https://moodle.example.edu/pluginfile.php/123/brief.pdf?forcedownload=1">Duplicate</a>
        """

        links = _discover_pdf_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )

        self.assertEqual(
            links,
            ["https://moodle.example.edu/pluginfile.php/123/brief.pdf?forcedownload=1"],
        )

    def test_discover_pdf_links_skips_off_instance_urls(self) -> None:
        html = """
        <a href="https://evil.example/brief.pdf">External</a>
        <a href="//evil.example/brief.pdf">Protocol-relative external</a>
        <a href="/pluginfile.php/123/brief.pdf">Brief</a>
        """

        links = _discover_pdf_links(
            html,
            "https://moodle.example.edu/mod/assign/view.php?id=1",
            "https://moodle.example.edu",
        )

        self.assertEqual(links, ["https://moodle.example.edu/pluginfile.php/123/brief.pdf"])


if __name__ == "__main__":
    unittest.main()
