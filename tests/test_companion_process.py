"""End-to-end process smoke tests, including native Windows execution."""

import json
import os
import secrets
import subprocess
import sys
import time
import unittest

from alpha_core.companion_client import CompanionError, get_companion_status
from alpha_interfaces.companion import LinkSettings
from test_companion_link import free_port, raw_peer, response_bytes


def process_is_running(pid):
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
    # Query the real interpreter process, not the Windows venv launcher.
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE access only
    if not handle:
        return False
    try:
        return kernel.WaitForSingleObject(handle, 0) == 258  # WAIT_TIMEOUT = still running
    finally:
        kernel.CloseHandle(handle)


class CompanionProcessTests(unittest.TestCase):
    def setUp(self):
        self.token = secrets.token_urlsafe(32)
        self.port = free_port()
        self.environment = {"ALPHA_ENV": "test", "ALPHA_LOG_LEVEL": "INFO",
                            "ALPHA_COMPANION_TOKEN": self.token,
                            "ALPHA_COMPANION_PORT": str(self.port),
                            "ALPHA_COMPANION_TIMEOUT": "0.5"}
        if sys.platform == "win32":
            self.environment["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
        self.process = None

    def tearDown(self):
        if self.process:
            if self.process.poll() is None:
                self.process.stdin.close()
                self.process.stdin = None
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            self.process.communicate(timeout=5)

    def launch(self):
        self.process = subprocess.Popen(
            [sys.executable, "-m", "alpha_companion", "--shutdown-on-stdin"],
            env=self.environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.fail("Companion exited before readiness")
            try:
                status = get_companion_status(LinkSettings(self.token, self.port, 0.1))
                self.assertTrue(process_is_running(status.pid))
                self.service_pid = status.pid
                return
            except CompanionError:
                time.sleep(0.05)
        self.fail("Companion did not become ready")

    def core(self, *args, environment=None):
        return subprocess.run([sys.executable, "-m", "alpha_core", "companion-status", *args],
                              env=self.environment if environment is None else environment,
                              capture_output=True, text=True, timeout=5)

    def test_end_to_end_status_authentication_shutdown_and_offline(self):
        self.launch()
        result = self.core("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(result.stdout)
        self.assertEqual(status["pid"], self.service_pid)
        self.assertNotEqual(status["pid"], os.getpid())
        if sys.platform == "win32":
            self.assertEqual(status["platform"], "Windows")
        human = self.core()
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn(f"PID {self.service_pid}", human.stdout)
        rejected = self.core(environment={**self.environment, "ALPHA_COMPANION_TOKEN": secrets.token_urlsafe(32)})
        self.assertEqual(rejected.returncode, 3)
        self.assertIn("rejected authentication", rejected.stderr)
        self.process.stdin.write("stop\n")
        self.process.stdin.flush()
        stdout, stderr = self.process.communicate(timeout=5)
        self.assertEqual(self.process.returncode, 0, stderr)
        self.assertFalse(process_is_running(self.service_pid))
        self.assertIn("stopped cleanly", stderr)
        self.assertEqual(stdout, "")
        self.assertNotIn(self.token, stderr + result.stdout + rejected.stderr)
        offline = self.core(environment={**self.environment, "ALPHA_COMPANION_TIMEOUT": "3"})
        self.assertEqual(offline.returncode, 4, offline.stderr)
        self.assertIn("Cannot connect", offline.stderr)

    def test_eof_shutdown(self):
        self.launch()
        _, stderr = self.process.communicate(timeout=5)
        self.assertEqual(self.process.returncode, 0, stderr)
        self.assertIn("stopped cleanly", stderr)

    def test_occupied_port_cli_error(self):
        self.launch()
        result = subprocess.run([sys.executable, "-m", "alpha_companion"], env=self.environment,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 4)
        self.assertIn("port may be occupied", result.stderr)

    def test_missing_token_cli_error(self):
        environment = {key: value for key, value in self.environment.items() if key != "ALPHA_COMPANION_TOKEN"}
        for module, args in (("alpha_core", ["companion-status"]), ("alpha_companion", [])):
            result = subprocess.run([sys.executable, "-m", module, *args], env=environment,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertIn("ALPHA_COMPANION_TOKEN", result.stderr)

    def test_timeout_cli_error(self):
        with raw_peer(None) as settings:
            result = self.core(environment={**self.environment,
                                           "ALPHA_COMPANION_PORT": str(settings.port),
                                           "ALPHA_COMPANION_TIMEOUT": "0.1"})
        self.assertEqual(result.returncode, 5)
        self.assertIn("timed out", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_invalid_response_cli_error(self):
        with raw_peer(response_bytes(b"{}")) as settings:
            result = self.core(environment={**self.environment,
                                           "ALPHA_COMPANION_PORT": str(settings.port)})
        self.assertEqual(result.returncode, 6)
        self.assertIn("invalid or incompatible", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
