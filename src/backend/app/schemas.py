"""DTO theo docs/contracts/mvp-api.md. Wire format giữ snake_case; mọi field bắt buộc trừ khi nullable."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Metric = Literal["power_kw", "energy_kwh"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BuildingSummary(Strict):
    building_id: str
    name: str
    energy_kwh: float | None = Field(description="Tổng điện năng ghi nhận; null khi không có interval (khác 0 kWh).")
    unit: Literal["kWh"]
    start: datetime
    end: datetime
    included_interval_count: int = Field(ge=0)
    coverage: Literal["complete", "partial", "none"]
    coverage_ratio: float = Field(ge=0, le=1)
    data_stale: bool


class Device(Strict):
    device_id: str
    building_id: str
    name: str
    enabled: bool
    status: Literal["online", "offline", "unknown", "disabled"]
    last_seen: datetime | None
    latest_event_time: datetime | None
    data_stale: bool
    period_seconds: int = Field(gt=0)


class Reading(Strict):
    message_id: str
    device_id: str
    building_id: str
    metric: Metric
    event_time: datetime
    received_at: datetime
    interval_start: datetime | None
    value: float = Field(ge=0)
    unit: Literal["kW", "kWh"]
    is_late: bool
    is_out_of_order: bool


class Alert(Strict):
    alert_id: str
    message_id: str
    device_id: str
    building_id: str
    event_time: datetime
    detected_at: datetime
    metric: Literal["power_kw"]
    value: float
    threshold: float
    unit: Literal["kW"]
    description: str


class MetaBase(Strict):
    generated_at: datetime


class SummaryMeta(MetaBase):
    start: datetime
    end: datetime
    building_id: str | None
    next_cursor: None = None


class DeviceListMeta(MetaBase):
    building_id: str | None
    next_cursor: str | None


class HistoryMeta(MetaBase):
    device_id: str
    metric: Metric
    start: datetime
    end: datetime
    next_cursor: str | None


class AlertListMeta(MetaBase):
    building_id: str | None
    device_id: str | None
    next_cursor: str | None


class SummaryResponse(Strict):
    data: list[BuildingSummary]
    meta: SummaryMeta


class DeviceListResponse(Strict):
    data: list[Device]
    meta: DeviceListMeta


class HistoryResponse(Strict):
    data: list[Reading]
    meta: HistoryMeta


class AlertListResponse(Strict):
    data: list[Alert]
    meta: AlertListMeta


class Ready(Strict):
    status: Literal["ready"]


class ReadyResponse(Strict):
    data: Ready
    meta: MetaBase


class ErrorBody(Strict):
    code: Literal["INVALID_QUERY", "FILTER_MISMATCH", "INVALID_CURSOR", "NOT_FOUND", "DEPENDENCY_UNAVAILABLE", "INTERNAL_ERROR"]
    message: str
    request_id: str


class ErrorResponse(Strict):
    error: ErrorBody
