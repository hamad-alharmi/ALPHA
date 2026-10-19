"""Run Companion in the foreground, optionally supervised through stdin."""

import argparse
import signal
import sys
from threading import Event, Thread

from alpha_core.config import load_settings
from alpha_core.errors import ConfigurationError
from alpha_core.logging_config import configure_logging
from alpha_interfaces.companion import HOST, LinkConfigurationError, load_link_settings
from alpha_companion.server import CompanionServer


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ALPHA Companion local status service")
    parser.add_argument("--shutdown-on-stdin", action="store_true",
                        help="Stop cleanly on stdin EOF or a line containing stop (for supervising processes)")
    args = parser.parse_args(argv)
    logger = configure_logging()
    stop = Event()
    previous = {}
    try:
        logger = configure_logging(load_settings().log_level)
        settings = load_link_settings()
        try:
            server = CompanionServer(settings)
        except OSError:
            logger.error(f"Cannot bind Companion to {HOST}:{settings.port}; port may be occupied or unavailable")
            return 4
        with server:
            for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
                if hasattr(signal, name):
                    signum = getattr(signal, name)
                    previous[signum] = signal.signal(signum, lambda *_: stop.set())
            if args.shutdown_on_stdin:
                def watch_stdin():
                    for line in sys.stdin:
                        if line.strip() == "stop":
                            break
                    stop.set()
                Thread(target=watch_stdin, daemon=True).start()
            logger.info(f"Companion listening on http://{HOST}:{settings.port}")
            server.run(stop)
        logger.info("Companion stopped cleanly")
        return 0
    except (ConfigurationError, LinkConfigurationError) as exc:
        logger.error(str(exc))
        return 2
    except Exception:
        logger.error("Companion failed unexpectedly")
        return 1
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
