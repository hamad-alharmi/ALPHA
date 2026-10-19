"""Expected application errors with safe, user-facing messages."""


class ConfigurationError(ValueError):
    """An environment setting is invalid."""
