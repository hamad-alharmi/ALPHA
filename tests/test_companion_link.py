import http.client
import json
import os
import platform
import secrets
import socket
import threading
import time
import unittest
from contextlib import contextmanager
from importlib.metadata import version
from unittest.mock import patch

from alpha_companion.server import CompanionServer
from alpha_core.companion_client import (
    AuthenticationError, CompanionTimeout, ConnectionFailure, InvalidResponse, get_companion_status,
)
from alpha_interfaces.companion import HOST, LinkSettings, STATUS_PATH


def free_port():
    with socket.socket() as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


@contextmanager
def running_server():
    settings = LinkSettings(secrets.token_urlsafe(32), free_port())
    stop = threading.Event()
    with CompanionServer(settings) as server:
        thread = threading.Thread(target=server.run, args=(stop,))
        thread.start()
        try:
            yield server, settings
        finally:
            stop.set()
            thread.join(timeout=3)
            if thread.is_alive():
                raise AssertionError("Server did not stop")


@contextmanager
def raw_peer(response: bytes | None):
    """Real loopback peer for malformed responses and read timeouts."""
    done = threading.Event()
    with socket.socket() as listener:
        listener.bind((HOST, 0))
        listener.listen()
        listener.settimeout(2)
        settings = LinkSettings(secrets.token_urlsafe(32), listener.getsockname()[1], 0.1)

        def respond():
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    connection.recv(8192)
                    if response is None:
                        done.wait(2)
                    else:
                        connection.sendall(response)
            except OSError:
                pass

        thread = threading.Thread(target=respond)
        thread.start()
        try:
            yield settings
        finally:
            done.set()
            thread.join(timeout=3)
            if thread.is_alive():
                raise AssertionError("Test peer did not stop")


def response_bytes(body, content_type="application/json", status=200):
    return (f"HTTP/1.0 {status} Test\r\nContent-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n\r\n").encode() + body


class CompanionLinkTests(unittest.TestCase):
    def test_authenticated_real_status(self):
        with running_server() as (server, settings):
            self.assertEqual(server.server_address, (HOST, settings.port))
            before = get_companion_status(settings)
            time.sleep(0.02)
            after = get_companion_status(settings)
            self.assertEqual(before.pid, os.getpid())
            self.assertEqual(before.platform, platform.system())
            self.assertEqual(before.version, version("alpha-foundation"))
            self.assertEqual(before.python_version, platform.python_version())
            self.assertGreater(after.uptime_seconds, before.uptime_seconds)

    def test_missing_wrong_and_duplicate_authentication(self):
        with running_server() as (_, settings):
            for values in ([], ["Bearer wrong"], ["Bearer " + settings.token] * 2):
                with self.subTest(count=len(values)):
                    connection = http.client.HTTPConnection(HOST, settings.port, timeout=2)
                    try:
                        connection.putrequest("GET", STATUS_PATH)
                        for value in values:
                            connection.putheader("Authorization", value)
                        connection.endheaders()
                        response = connection.getresponse()
                        self.assertEqual(response.status, 401)
                        self.assertEqual(json.loads(response.read()), {"error": "unauthorized"})
                    finally:
                        connection.close()

    def test_client_authentication_error(self):
        with running_server() as (_, settings):
            with self.assertRaises(AuthenticationError):
                get_companion_status(LinkSettings(secrets.token_urlsafe(32), settings.port))

    def test_unknown_path_and_method(self):
        with running_server() as (_, settings):
            for method, path, expected in (("GET", "/v2/status", 404), ("POST", STATUS_PATH, 501)):
                connection = http.client.HTTPConnection(HOST, settings.port, timeout=2)
                try:
                    connection.request(method, path, headers={"Authorization": "Bearer " + settings.token})
                    self.assertEqual(connection.getresponse().status, expected)
                finally:
                    connection.close()

    def test_offline(self):
        with self.assertRaises(ConnectionFailure):
            get_companion_status(LinkSettings(secrets.token_urlsafe(32), free_port(), 3))

    def test_real_socket_read_timeout(self):
        with raw_peer(None) as settings:
            started = time.monotonic()
            with self.assertRaises(CompanionTimeout):
                get_companion_status(settings)
            self.assertLess(time.monotonic() - started, 1)

    def test_connection_timeout_classification(self):
        # Deterministically exercise connect timeout; loopback refusal is immediate.
        with patch("http.client.HTTPConnection.connect", side_effect=TimeoutError):
            with self.assertRaises(CompanionTimeout):
                get_companion_status(LinkSettings(secrets.token_urlsafe(32)))

    def test_invalid_http_json_and_framing(self):
        responses = [b"not http\r\n\r\n", response_bytes(b"not JSON"),
                     response_bytes(b"{}", "text/html"), response_bytes(b"{}", status=500),
                     response_bytes(b"{}", status=302), response_bytes(b"x" * 8193),
                     b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: 50\r\n\r\n{}",
                     b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n{}",
                     b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + b"9" * 5000 + b"\r\n\r\n{}"]
        for response in responses:
            with self.subTest(response=response[:30]), raw_peer(response) as settings:
                with self.assertRaises(InvalidResponse):
                    get_companion_status(settings)

    def test_invalid_status_contract(self):
        valid = {"protocol_version": 1, "component": "alpha-companion", "status": "ok",
                 "pid": 10, "platform": "Windows", "version": "0.2.0",
                 "python_version": "3.14.3", "uptime_seconds": 1.0}
        variants = [[], {}, {**valid, "extra": 1}]
        variants.extend({**valid, key: value} for key, value in (
            ("protocol_version", 2), ("protocol_version", True), ("pid", True),
            ("pid", -1), ("component", "other"), ("uptime_seconds", -1),
            ("uptime_seconds", float("nan")), ("uptime_seconds", True),
            ("platform", "\x1b[31m"), ("version", ""), ("python_version", None)))
        for data in variants:
            with self.subTest(data=data), raw_peer(response_bytes(json.dumps(data).encode())) as settings:
                with self.assertRaises(InvalidResponse):
                    get_companion_status(settings)

    def test_occupied_port(self):
        with running_server() as (_, settings):
            with self.assertRaises(OSError):
                CompanionServer(settings)

    def test_graceful_shutdown_releases_socket(self):
        with running_server() as (_, settings):
            self.assertEqual(get_companion_status(settings).status, "ok")
        with self.assertRaises(ConnectionFailure):
            get_companion_status(settings)
