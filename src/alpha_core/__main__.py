"""One-shot startup and local health CLI."""

import argparse
import json
from collections.abc import Sequence

from alpha_core.config import load_settings
from alpha_core.errors import ConfigurationError
from alpha_core.health import check_health
from alpha_core.logging_config import configure_logging


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ALPHA Core foundation")
    parser.add_argument("command", nargs="?", choices=("start", "health"), default="start")
    args = parser.parse_args(argv)
    logger = configure_logging()
    try:
        settings = load_settings()
        logger = configure_logging(settings.log_level)
        report = check_health()
        if args.command == "health":
            print(json.dumps(report.to_dict()))
        else:
            logger.info("ALPHA Core foundation initialized")
        return 0
    except ConfigurationError as exc:
        logger.error(str(exc))
        return 2
    except Exception:
        # Exception text and tracebacks may contain secrets. Keep CLI output safe.
        logger.error("ALPHA Core initialization failed unexpectedly")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
