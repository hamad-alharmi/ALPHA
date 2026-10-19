"""Version 1 local link configuration and status contract; no Core dependency."""

import math
import os
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field

HOST = "127.0.0.1"
STATUS_PATH = "/v1/status"
PROTOCOL_VERSION = 1
MAX_RESPONSE_BYTES = 8192


class LinkConfigurationError(ValueError):
    """Invalid link settings; messages never include supplied values."""


@dataclass(frozen=True)
class LinkSettings:
    token: str = field(repr=False)
    port: int = 8765
    timeout: float = 3.0

    def __post_init__(self):
        if (not isinstance(self.token, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", self.token)):
            raise LinkConfigurationError(
                "ALPHA_COMPANION_TOKEN must be a generated URL-safe token of 43–128 characters"
            )
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise LinkConfigurationError("ALPHA_COMPANION_PORT must be an integer from 1 to 65535")
        if (isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float))
                or not math.isfinite(self.timeout) or not 0.05 <= self.timeout <= 30):
            raise LinkConfigurationError("ALPHA_COMPANION_TIMEOUT must be between 0.05 and 30 seconds")


def load_link_settings(environ: Mapping[str, str] | None = None) -> LinkSettings:
    source = os.environ if environ is None else environ
    # Refuse accidental attempts to enable remote access; no configurable URL.
    if source.get("ALPHA_COMPANION_HOST", HOST) != HOST:
        raise LinkConfigurationError("ALPHA_COMPANION_HOST must be 127.0.0.1")
    try:
        port = int(source.get("ALPHA_COMPANION_PORT", "8765"))
    except ValueError:
        raise LinkConfigurationError("ALPHA_COMPANION_PORT must be an integer from 1 to 65535") from None
    try:
        timeout = float(source.get("ALPHA_COMPANION_TIMEOUT", "3"))
    except ValueError:
        raise LinkConfigurationError("ALPHA_COMPANION_TIMEOUT must be between 0.05 and 30 seconds") from None
    return LinkSettings(source.get("ALPHA_COMPANION_TOKEN", ""), port, timeout)


@dataclass(frozen=True)
class CompanionStatus:
    protocol_version: int
    component: str
    status: str
    pid: int
    platform: str
    version: str
    python_version: str
    uptime_seconds: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: object) -> "CompanionStatus":
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise ValueError("Invalid status fields")
        if type(data["protocol_version"]) is not int or data["protocol_version"] != PROTOCOL_VERSION:
            raise ValueError("Unsupported protocol version")
        if data["component"] != "alpha-companion" or data["status"] != "ok":
            raise ValueError("Invalid component or status")
        if type(data["pid"]) is not int or data["pid"] <= 0:
            raise ValueError("Invalid process ID")
        for key in ("platform", "version", "python_version"):
            value = data[key]
            if (not isinstance(value, str) or not 1 <= len(value) <= 200
                    or not value.isascii() or not value.isprintable()):
                raise ValueError("Invalid runtime information")
        uptime = data["uptime_seconds"]
        if type(uptime) not in (int, float) or not math.isfinite(uptime) or uptime < 0:
            raise ValueError("Invalid uptime")
        return cls(**data)
