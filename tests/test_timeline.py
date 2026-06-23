import unittest

from scrapers import timeline


class FakeResponse:
    def __init__(self, payload, text: str = "{}") -> None:
        self._payload = payload
        self.text = text

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def post(self, url: str, json):
        return self.response


class TestTimelineScraper(unittest.TestCase):
    def setUp(self) -> None:
        timeline._ACTIVE_COURSE_IDS_CACHE.clear()

    def test_get_active_course_ids_raises_on_moodle_error(self) -> None:
        client = FakeClient(FakeResponse([{"error": True, "exception": "boom"}], text="error"))

        with self.assertRaises(RuntimeError):
            timeline._get_active_course_ids(client, "https://moodle.example.edu", "sess")

    def test_get_active_course_ids_raises_on_unexpected_shape(self) -> None:
        client = FakeClient(FakeResponse([{"data": {}}], text="{}"))

        with self.assertRaises(RuntimeError):
            timeline._get_active_course_ids(client, "https://moodle.example.edu", "sess")

    def test_get_active_course_ids_returns_course_ids(self) -> None:
        client = FakeClient(
            FakeResponse(
                [{"data": {"courses": [{"id": 101}, {"id": 202}, {"name": "missing id"}]}}],
                text="{}",
            )
        )

        self.assertEqual(
            timeline._get_active_course_ids(client, "https://moodle.example.edu", "sess"),
            {101, 202},
        )

    def test_fetch_deadlines_rejects_invalid_days_before_network(self) -> None:
        with self.assertRaises(ValueError):
            timeline._fetch_deadlines_from_api(days=0)


if __name__ == "__main__":
    unittest.main()
