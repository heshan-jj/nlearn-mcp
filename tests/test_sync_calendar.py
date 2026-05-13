import datetime
import unittest
from unittest.mock import patch

from scrapers.timeline import Deadline
from tools.sync_calendar import get_deadlines_for_sync


class TestSyncCalendar(unittest.TestCase):
    def test_get_deadlines_for_sync_formats_due_date_and_description(self) -> None:
        due = 1_750_000_000  # fixed unix timestamp for stable formatting

        d = Deadline(
            id=123,
            name="HW1",
            course_name="CS101",
            due_date=due,
            url="https://nelearn.example/mod/assign/view.php?id=1",
            action_name="Turn in",
            action_url=None,  # ensure fallback to d.url
        )

        with patch("tools.sync_calendar.get_deadlines", return_value=[d]):
            result = get_deadlines_for_sync(days=14)

        self.assertEqual(len(result), 1)
        item = result[0]

        expected_iso = datetime.datetime.fromtimestamp(due).strftime("%Y-%m-%dT%H:%M:%S")
        self.assertEqual(item["due_date"], expected_iso)
        self.assertEqual(item["reminder_minutes"], 1440)
        self.assertIn("Course: CS101", item["description"])
        self.assertIn("Task: HW1", item["description"])
        self.assertIn("Link: " + d.url, item["description"])
        self.assertEqual(item["title"], "CS101 - HW1")


if __name__ == "__main__":
    unittest.main()

