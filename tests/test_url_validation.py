import unittest

from utils.url_validation import url_belongs_to_instance
from utils.validation import validate_days


class TestUrlValidation(unittest.TestCase):
    def test_url_belongs_to_instance_accepts_same_origin(self) -> None:
        self.assertTrue(
            url_belongs_to_instance(
                "https://moodle.example.edu/mod/assign/view.php?id=1",
                "https://moodle.example.edu",
            )
        )

    def test_url_belongs_to_instance_rejects_different_host(self) -> None:
        self.assertFalse(
            url_belongs_to_instance(
                "https://evil.example/mod/assign/view.php?id=1",
                "https://moodle.example.edu",
            )
        )

    def test_url_belongs_to_instance_rejects_non_default_port(self) -> None:
        self.assertFalse(
            url_belongs_to_instance(
                "https://moodle.example.edu:444/mod/assign/view.php?id=1",
                "https://moodle.example.edu",
            )
        )

    def test_url_belongs_to_instance_enforces_base_path(self) -> None:
        self.assertFalse(
            url_belongs_to_instance(
                "https://moodle.example.edu/other/mod/assign/view.php?id=1",
                "https://moodle.example.edu/moodle",
            )
        )


class TestDaysValidation(unittest.TestCase):
    def test_validate_days_accepts_valid_integer(self) -> None:
        self.assertEqual(validate_days(14), 14)

    def test_validate_days_rejects_invalid_values(self) -> None:
        for value in (0, -1, 366, True, "14"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_days(value)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
