"""Mô hình dữ liệu theo docs/architecture/mvp-system.md (đề xuất baseline #27)."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR, Boolean, CheckConstraint, LargeBinary, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

ID_REGEX = "^[A-Za-z0-9_-]{1,64}$"


class Base(DeclarativeBase):
    pass


class Building(Base):
    __tablename__ = "buildings"
    building_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    __table_args__ = (CheckConstraint(f"building_id ~ '{ID_REGEX}'", name="ck_buildings_id_format"),)


class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    period_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    power_threshold_kw: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(f"device_id ~ '{ID_REGEX}'", name="ck_devices_id_format"),
        CheckConstraint("period_seconds > 0", name="ck_devices_period_positive"),
        CheckConstraint("power_threshold_kw >= 0", name="ck_devices_threshold_nonneg"),
        Index("ix_devices_building_id", "building_id"),
    )


class Reading(Base):
    __tablename__ = "readings"
    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    metric: Mapped[str] = mapped_column(String(16), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    value: Mapped[Decimal] = mapped_column(Numeric(24, 9), nullable=False)
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_out_of_order: Mapped[bool] = mapped_column(Boolean, nullable=False)
    period_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (
        CheckConstraint("metric IN ('power_kw','energy_kwh')", name="ck_readings_metric"),
        CheckConstraint("value >= 0", name="ck_readings_value_nonneg"),
        CheckConstraint("(metric = 'energy_kwh') = (interval_start IS NOT NULL)", name="ck_readings_interval_iff_energy"),
        CheckConstraint("interval_start IS NULL OR interval_start < event_time", name="ck_readings_interval_before_event"),
        CheckConstraint("period_seconds > 0", name="ck_readings_period_positive"),
        UniqueConstraint("device_id", "metric", "event_time", name="uq_readings_device_metric_event"),
        # Lớp bảo vệ cuối chống chồng interval energy của cùng device (cần extension btree_gist).
        ExcludeConstraint(
            ("device_id", "="),
            (func.tstzrange(text("interval_start"), text("event_time"), text("'[)'")), "&&"),
            name="ex_readings_energy_no_overlap",
            where=text("metric = 'energy_kwh'"),
            using="gist",
        ),
        Index("ix_readings_history", "device_id", "metric", "event_time", "message_id"),
    )


class Alert(Base):
    __tablename__ = "alerts"
    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("readings.message_id"), nullable=False, unique=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value_kw: Mapped[Decimal] = mapped_column(Numeric(24, 9), nullable=False)
    threshold_kw: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint("value_kw > threshold_kw", name="ck_alerts_over_threshold"),
        Index("ix_alerts_detected", "detected_at", "alert_id"),
    )


class ExportClient(Base):
    """Client máy (CLI/script) được cấp token để xuất dữ liệu. Không phải tài khoản người dùng Dashboard."""
    __tablename__ = "export_clients"
    client_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    token_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    can_export: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint(f"client_id ~ '{ID_REGEX}'", name="ck_export_clients_id_format"),
        CheckConstraint("token_sha256 ~ '^[0-9a-f]{64}$'", name="ck_export_clients_token_hex"),
        UniqueConstraint("token_sha256", name="uq_export_clients_token"),
    )


class ExportClientScope(Base):
    __tablename__ = "export_client_scopes"
    client_id: Mapped[str] = mapped_column(ForeignKey("export_clients.client_id", ondelete="CASCADE"), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), primary_key=True)


class Export(Base):
    __tablename__ = "exports"
    export_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("export_clients.client_id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), nullable=False)
    metric: Mapped[str] = mapped_column(String(16), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        # Guard idempotency/concurrency: một export cho mỗi (client, Idempotency-Key).
        UniqueConstraint("client_id", "idempotency_key", name="uq_exports_client_key"),
        CheckConstraint("metric IN ('power_kw','energy_kwh')", name="ck_exports_metric"),
        CheckConstraint("start_at < end_at", name="ck_exports_range_order"),
        CheckConstraint("end_at - start_at <= interval '31 days'", name="ck_exports_range_max_31d"),
        CheckConstraint("row_count >= 0", name="ck_exports_row_count_nonneg"),
    )
