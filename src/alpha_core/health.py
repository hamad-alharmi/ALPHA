"""Local readiness after configuration and logging initialization."""

from alpha_interfaces.health import HealthReport


def check_health() -> HealthReport:
    """Report foundation readiness only; no external dependencies are probed."""
    return HealthReport()
