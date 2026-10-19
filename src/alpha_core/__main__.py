"""One-shot startup and local health CLI."""

import argparse
import json
from collections.abc import Sequence

from alpha_core.config import load_settings
from alpha_core.errors import ConfigurationError
from alpha_core.health import check_health
from alpha_core.logging_config import configure_logging
from alpha_core.companion_client import CompanionError, get_companion_status
from alpha_interfaces.companion import LinkConfigurationError, load_link_settings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ALPHA Core foundation")
    parser.add_argument("command", nargs="?", choices=("start", "health", "companion-status"), default="start")
    parser.add_argument("--json", action="store_true", help="Emit Companion status as JSON")
    args = parser.parse_args(argv)
    logger = configure_logging()
    try:
        settings = load_settings()
        logger = configure_logging(settings.log_level)
        if args.command == "companion-status":
            status = get_companion_status(load_link_settings())
            if args.json:
                print(json.dumps(status.to_dict()))
            else:
                print(f"Companion: {status.status} | PID {status.pid} | {status.platform} | "
                      f"version {status.version} | Python {status.python_version} | "
                      f"uptime {status.uptime_seconds:.2f}s | protocol {status.protocol_version}")
            return 0
        report = check_health()
        if args.command == "health":
            print(json.dumps(report.to_dict()))
        else:
            logger.info("ALPHA Core foundation initialized")
        return 0
    except (ConfigurationError, LinkConfigurationError) as exc:
        logger.error(str(exc))
        return 2
    except CompanionError as exc:
        logger.error(str(exc))
        return exc.exit_code
    except Exception:
        # Exception text and tracebacks may contain secrets. Keep CLI output safe.
        logger.error("ALPHA Core initialization failed unexpectedly")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
