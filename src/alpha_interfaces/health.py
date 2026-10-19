"""Minimal local health result; not a network protocol or device contract."""

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class HealthReport:
    component: Literal["alpha-core"] = "alpha-core"
    status: Literal["ok"] = "ok"
    scope: Literal["foundation"] = "foundation"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
