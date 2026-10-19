import io
import json
import unittest
from datetime import datetime, timedelta

from alpha_core.logging_config import configure_logging


class LoggingTests(unittest.TestCase):
    def test_json_fields_and_utc_timestamp(self):
        output = io.StringIO()
        logger = configure_logging(stream=output)
        logger.info('A message with "quotes" and\na newline')
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        event = json.loads(output.getvalue())
        self.assertEqual(event["level"], "INFO")
        self.assertEqual(event["logger"], "alpha")
        self.assertEqual(event["message"], 'A message with "quotes" and\na newline')
        self.assertEqual(datetime.fromisoformat(event["timestamp"]).utcoffset(), timedelta(0))

    def test_level_filtering(self):
        output = io.StringIO()
        logger = configure_logging("WARNING", stream=output)
        logger.info("hidden")
        logger.warning("visible")
        self.assertEqual(json.loads(output.getvalue())["message"], "visible")

    def test_reconfiguration_does_not_duplicate_events(self):
        output = io.StringIO()
        configure_logging(stream=output)
        logger = configure_logging(stream=output)
        logger.info("once")
        self.assertEqual(len(output.getvalue().splitlines()), 1)
