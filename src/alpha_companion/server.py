"""Small loopback-only HTTP status service with authenticated requests."""

import hmac
import json
import logging
import os
import platform
import socket
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.metadata import version
from threading import Event

from alpha_interfaces.companion import (
    HOST, PROTOCOL_VERSION, STATUS_PATH, CompanionStatus, LinkSettings,
)


class CompanionServer(HTTPServer):
    allow_reuse_address = False

    def __init__(self, settings: LinkSettings):
        self.settings = settings
        self.started_at = time.monotonic()
        self.app_version = version("alpha-foundation")
        super().__init__((HOST, settings.port), StatusHandler)
        self.timeout = 0.1

    def server_bind(self):
        # Windows SO_REUSEADDR can let another socket steal an occupied port.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(0.5)
        return connection, address

    def handle_error(self, request, client_address):
        # Never dump request data or exception text to stderr.
        logging.getLogger("alpha").warning("Companion request failed")

    def run(self, stop: Event):
        while not stop.is_set():
            self.handle_request()

    def status(self) -> CompanionStatus:
        return CompanionStatus(
            PROTOCOL_VERSION, "alpha-companion", "ok", os.getpid(),
            platform.system(), self.app_version, platform.python_version(),
            round(time.monotonic() - self.started_at, 6),
        )


class StatusHandler(BaseHTTPRequestHandler):
    # One request per connection, no keepalive, body uploads, or static files.
    server_version = "ALPHA"
    sys_version = ""

    def log_message(self, format, *args):
        pass  # Default access logs can include attacker-controlled request text.

    def respond(self, code: int, data: dict):
        body = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        if code == 401:
            self.send_header("WWW-Authenticate", "Bearer")
        self.end_headers()
        self.close_connection = True
        self.wfile.write(body)

    def do_GET(self):
        credentials = self.headers.get_all("Authorization", [])
        expected = ("Bearer " + self.server.settings.token).encode("ascii")
        if len(credentials) != 1 or not hmac.compare_digest(credentials[0].encode("utf-8"), expected):
            self.respond(401, {"error": "unauthorized"})
            return
        if self.path != STATUS_PATH:
            self.respond(404, {"error": "not_found"})
            return
        self.respond(200, self.server.status().to_dict())
