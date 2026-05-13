import os
import unittest

from auth.session import COOKIES_FILE, session_scope


class TestAuthSessionIntegration(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("RUN_LIVE_INTEGRATION_TESTS") == "1", "live integration disabled")
    def test_session_scope_can_authenticate(self) -> None:
        # This test requires a working NLEARN_URL and NLEARN_USERNAME/NLEARN_PASSWORD.
        # It is skipped by default to keep CI/local runs deterministic.
        with session_scope() as client:
            # At minimum, we should have the cookie jar populated.
            self.assertTrue(len(dict(client.cookies)) > 0)

        # Optionally, cached cookie file should exist after a successful login.
        self.assertTrue(COOKIES_FILE.exists())


if __name__ == "__main__":
    unittest.main()

