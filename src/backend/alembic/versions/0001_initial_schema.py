"""Schema MVP: buildings, devices, readings, alerts (+ btree_gist, EXCLUDE chống chồng interval)

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ID = "'^[A-Za-z0-9_-]{1,64}$'"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(f"""
        CREATE TABLE buildings (
            building_id varchar(64) PRIMARY KEY,
            name varchar(200) NOT NULL,
            CONSTRAINT ck_buildings_id_format CHECK (building_id ~ {ID})
        )""")
    op.execute(f"""
        CREATE TABLE devices (
            device_id varchar(64) PRIMARY KEY,
            building_id varchar(64) NOT NULL REFERENCES buildings(building_id),
            name varchar(200) NOT NULL,
            enabled boolean NOT NULL DEFAULT true,
            period_seconds integer NOT NULL,
            power_threshold_kw numeric(18,9) NOT NULL,
            last_seen timestamptz,
            latest_event_time timestamptz,
            CONSTRAINT ck_devices_id_format CHECK (device_id ~ {ID}),
            CONSTRAINT ck_devices_period_positive CHECK (period_seconds > 0),
            CONSTRAINT ck_devices_threshold_nonneg CHECK (power_threshold_kw >= 0)
        )""")
    op.execute("CREATE INDEX ix_devices_building_id ON devices (building_id)")
    op.execute("""
        CREATE TABLE readings (
            message_id varchar(36) PRIMARY KEY,
            device_id varchar(64) NOT NULL REFERENCES devices(device_id),
            metric varchar(16) NOT NULL,
            event_time timestamptz NOT NULL,
            received_at timestamptz NOT NULL,
            interval_start timestamptz,
            value numeric(24,9) NOT NULL,
            is_late boolean NOT NULL,
            is_out_of_order boolean NOT NULL,
            period_seconds integer NOT NULL,
            CONSTRAINT ck_readings_metric CHECK (metric IN ('power_kw','energy_kwh')),
            CONSTRAINT ck_readings_value_nonneg CHECK (value >= 0),
            CONSTRAINT ck_readings_interval_iff_energy CHECK ((metric = 'energy_kwh') = (interval_start IS NOT NULL)),
            CONSTRAINT ck_readings_interval_before_event CHECK (interval_start IS NULL OR interval_start < event_time),
            CONSTRAINT ck_readings_period_positive CHECK (period_seconds > 0),
            CONSTRAINT uq_readings_device_metric_event UNIQUE (device_id, metric, event_time),
            CONSTRAINT ex_readings_energy_no_overlap EXCLUDE USING gist (
                device_id WITH =,
                tstzrange(interval_start, event_time, '[)') WITH &&
            ) WHERE (metric = 'energy_kwh')
        )""")
    op.execute("CREATE INDEX ix_readings_history ON readings (device_id, metric, event_time, message_id)")
    op.execute("""
        CREATE TABLE alerts (
            alert_id varchar(64) PRIMARY KEY,
            message_id varchar(36) NOT NULL UNIQUE REFERENCES readings(message_id),
            device_id varchar(64) NOT NULL REFERENCES devices(device_id),
            event_time timestamptz NOT NULL,
            detected_at timestamptz NOT NULL,
            value_kw numeric(24,9) NOT NULL,
            threshold_kw numeric(18,9) NOT NULL,
            description text NOT NULL,
            CONSTRAINT ck_alerts_over_threshold CHECK (value_kw > threshold_kw)
        )""")
    op.execute("CREATE INDEX ix_alerts_detected ON alerts (detected_at, alert_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS alerts")
    op.execute("DROP TABLE IF EXISTS readings")
    op.execute("DROP TABLE IF EXISTS devices")
    op.execute("DROP TABLE IF EXISTS buildings")
    # Không DROP EXTENSION btree_gist: extension có thể do DBA/đối tượng khác dùng.
