"""Bounded local HTTP requests. No proxies, redirects, or credential logging."""

import http.client
import json

from alpha_interfaces.companion import (
    HOST, MAX_RESPONSE_BYTES, STATUS_PATH, CompanionStatus, LinkSettings,
)


class CompanionError(Exception):
    """Safe CLI error with a stable exit code."""
    exit_code = 1


class AuthenticationError(CompanionError):
    exit_code = 3


class ConnectionFailure(CompanionError):
    exit_code = 4


class CompanionTimeout(CompanionError):
    exit_code = 5


class InvalidResponse(CompanionError):
    exit_code = 6


def get_companion_status(settings: LinkSettings) -> CompanionStatus:
    connection = http.client.HTTPConnection(HOST, settings.port, timeout=settings.timeout)
    try:
        connection.request("GET", STATUS_PATH, headers={
            "Authorization": "Bearer " + settings.token,
            "Accept": "application/json",
            "Connection": "close",
        })
        response = connection.getresponse()
        if response.status in (401, 403):
            raise AuthenticationError("Companion rejected authentication; configure the same token in both processes")
        if response.status != 200:
            raise InvalidResponse("Companion returned an unexpected HTTP status")
        if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise InvalidResponse("Companion returned a non-JSON response")
        # Version 1 requires a finite, explicit body length and no transfer coding.
        length = response.getheader("Content-Length", "")
        if (response.getheader("Transfer-Encoding") or len(length) > 5
                or not length.isascii() or not length.isdecimal()
                or not 1 <= int(length) <= MAX_RESPONSE_BYTES):
            raise InvalidResponse("Companion returned an invalid response length")
        body = response.read(int(length))
        if len(body) != int(length):
            raise InvalidResponse("Companion returned a truncated response")
        try:
            return CompanionStatus.from_dict(json.loads(body.decode("utf-8")))
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise InvalidResponse("Companion returned an invalid or incompatible status response") from None
    except TimeoutError:
        raise CompanionTimeout("Companion request timed out; check the service or increase ALPHA_COMPANION_TIMEOUT") from None
    except http.client.RemoteDisconnected:
        raise ConnectionFailure("Companion closed the connection without responding") from None
    except http.client.HTTPException:
        raise InvalidResponse("Companion returned an invalid HTTP response") from None
    except OSError:
        raise ConnectionFailure(f"Cannot connect to Companion at {HOST}:{settings.port}; start Companion and check its port") from None
    finally:
        connection.close()
