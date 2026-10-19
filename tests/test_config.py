import unittest

from alpha_core.config import Settings, load_settings
from alpha_core.errors import ConfigurationError


class ConfigurationTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(load_settings({}), Settings())

    def test_normalizes_supported_values(self):
        self.assertEqual(
            load_settings({"ALPHA_ENV": " TEST ", "ALPHA_LOG_LEVEL": "debug"}),
            Settings("test", "DEBUG"),
        )

    def test_accepts_all_documented_values(self):
        for environment in ("development", "test", "production"):
            for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                with self.subTest(environment=environment, level=level):
                    self.assertEqual(
                        load_settings({"ALPHA_ENV": environment, "ALPHA_LOG_LEVEL": level}),
                        Settings(environment, level),
                    )

    def test_invalid_values_are_rejected_without_echo(self):
        for key in ("ALPHA_ENV", "ALPHA_LOG_LEVEL"):
            for value in ("", " ", "sensitive-test-value"):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ConfigurationError) as caught:
                        load_settings({key: value})
                    self.assertIn(key, str(caught.exception))
                    self.assertNotIn("sensitive-test-value", str(caught.exception))

    def test_unknown_settings_are_ignored(self):
        self.assertEqual(load_settings({"UNRELATED": "ignored"}), Settings())
