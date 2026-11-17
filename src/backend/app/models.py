"""Mô hình dữ liệu theo docs/architecture/mvp-system.md (đề xuất baseline #27)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
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
