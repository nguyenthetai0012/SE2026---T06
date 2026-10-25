"""Domain-owned contracts. Domain modules (dashboard, reporting) depend on these
abstractions; the Ingestion module provides the implementation (DIP)."""

from dataclasses import dataclass
from typing import Protocol

UNITS = {"power_kw": "kW", "energy_kwh": "kWh"}  # [ĐỀ XUẤT] mapping, MQTT draft PR #10


@dataclass(frozen=True)
class Window:
    """Half-open time window [start, end) in ISO-8601 UTC."""
    start: str
    end: str


@dataclass(frozen=True)
class ReadingView:
    event_time: str
    received_at: str
    metric: str
    value: float


@dataclass(frozen=True)
class EnergyTotal:
    kwh: float
    reading_count: int


def round_kwh(value: float) -> float:
    return round(value or 0.0, 3)


class EnergyQueryPort(Protocol):
    def building_energy(self, building_id: str, window: Window) -> EnergyTotal: ...

    def energy_by_building(self, window: Window) -> dict[str, EnergyTotal]: ...

    def device_readings(self, device_id: str, window: Window) -> list[ReadingView]: ...

    def device_building(self, device_id: str) -> str | None: ...
