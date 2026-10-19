"""JSON events on stderr; application callers must use fixed safe messages."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import TextIO


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })


def configure_logging(
    level: str = "INFO", stream: TextIO | None = None
) -> logging.Logger:
    logger = logging.getLogger("alpha")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    handler = logging.StreamHandler(sys.stderr if stream is None else stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
