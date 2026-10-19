import unittest

from alpha_core.health import check_health


class HealthTests(unittest.TestCase):
    def test_health_is_explicitly_limited_to_foundation(self):
        self.assertEqual(check_health().to_dict(), {
            "component": "alpha-core", "status": "ok", "scope": "foundation"
        })
