import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from alpha_core.__main__ import main


class CliTests(unittest.TestCase):
    def run_cli(self, *args, settings=None, cwd=None):
        # Do not forward or inspect the caller's environment or credentials.
        environment = {"ALPHA_ENV": "test", "ALPHA_LOG_LEVEL": "INFO"}
        if sys.platform == "win32":
            # Windows subprocesses may need this OS path, which is not a secret.
            environment["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
        environment.update(settings or {})
        return subprocess.run(
            [sys.executable, "-m", "alpha_core", *args],
            env=environment, cwd=cwd, capture_output=True, text=True, timeout=10,
            check=False,
        )

    def test_default_and_explicit_start(self):
        for args in ((), ("start",)):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(json.loads(result.stderr)["message"],
                                 "ALPHA Core foundation initialized")

    def test_health_stdout_is_json(self):
        result = self.run_cli("health")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["scope"], "foundation")
        self.assertEqual(result.stderr, "")

    def test_health_from_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli("health", cwd=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ok")

    def test_bad_configuration_fails_without_leaking_value(self):
        for key in ("ALPHA_ENV", "ALPHA_LOG_LEVEL"):
            with self.subTest(key=key):
                result = self.run_cli("health", settings={key: "sensitive-test-value"})
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertEqual(json.loads(result.stderr)["level"], "ERROR")
                self.assertNotIn("sensitive-test-value", result.stderr)

    def test_help(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("health", result.stdout)

    def test_unknown_command(self):
        result = self.run_cli("unknown")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid choice", result.stderr)

    def test_unexpected_error_is_safe_and_nonzero(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch("alpha_core.__main__.load_settings", side_effect=RuntimeError("private-detail")):
            with redirect_stdout(output), redirect_stderr(errors):
                result = main(["health"])
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(json.loads(errors.getvalue())["level"], "ERROR")
        self.assertNotIn("private-detail", errors.getvalue())
