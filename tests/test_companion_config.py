import secrets
import unittest

from alpha_interfaces.companion import LinkConfigurationError, LinkSettings, load_link_settings


class LinkConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.token = secrets.token_urlsafe(32)

    def test_defaults(self):
        settings = load_link_settings({"ALPHA_COMPANION_TOKEN": self.token})
        self.assertEqual(settings.port, 8765)
        self.assertEqual(settings.timeout, 3)

    def test_overrides(self):
        settings = load_link_settings({"ALPHA_COMPANION_TOKEN": self.token,
                                       "ALPHA_COMPANION_PORT": "9000", "ALPHA_COMPANION_TIMEOUT": "0.1"})
        self.assertEqual((settings.port, settings.timeout), (9000, 0.1))

    def test_token_is_required_and_never_echoed(self):
        for token in ("", "short", "a" * 42, "a" * 129, "a" * 43 + "\r\n", "é" * 43):
            with self.subTest(length=len(token)):
                with self.assertRaises(LinkConfigurationError):
                    load_link_settings({"ALPHA_COMPANION_TOKEN": token})
        self.assertNotIn(self.token, repr(LinkSettings(self.token)))

    def test_invalid_ports(self):
        for port in ("0", "-1", "65536", "abc", "1.5", ""):
            with self.subTest(port=port), self.assertRaises(LinkConfigurationError):
                load_link_settings({"ALPHA_COMPANION_TOKEN": self.token, "ALPHA_COMPANION_PORT": port})

    def test_invalid_timeouts(self):
        for timeout in ("nan", "inf", "-1", "0", "31", "invalid", ""):
            with self.subTest(timeout=timeout), self.assertRaises(LinkConfigurationError):
                load_link_settings({"ALPHA_COMPANION_TOKEN": self.token, "ALPHA_COMPANION_TIMEOUT": timeout})

    def test_remote_hosts_are_rejected(self):
        for host in ("0.0.0.0", "localhost", "::1", "example.com", ""):
            with self.subTest(host=host), self.assertRaises(LinkConfigurationError):
                load_link_settings({"ALPHA_COMPANION_TOKEN": self.token, "ALPHA_COMPANION_HOST": host})

    def test_direct_settings_are_validated(self):
        for kwargs in ({"port": True}, {"port": 0}, {"timeout": True}, {"timeout": float("nan")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(LinkConfigurationError):
                LinkSettings(self.token, **kwargs)
