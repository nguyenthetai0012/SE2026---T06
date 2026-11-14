"""Export API (BT3 VT-023): export_clients, export_client_scopes, exports

Guard idempotency/concurrency nằm ở DB: UNIQUE(client_id, idempotency_key) + INSERT ... ON CONFLICT trong app.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ID = "'^[A-Za-z0-9_-]{1,64}$'"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE export_clients (
            client_id varchar(64) PRIMARY KEY,
            name varchar(200) NOT NULL,
            token_sha256 char(64) NOT NULL,
            can_export boolean NOT NULL DEFAULT false,
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_export_clients_id_format CHECK (client_id ~ {ID}),
            CONSTRAINT ck_export_clients_token_hex CHECK (token_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT uq_export_clients_token UNIQUE (token_sha256)
        )""")
    op.execute("""
        CREATE TABLE export_client_scopes (
            client_id varchar(64) NOT NULL REFERENCES export_clients(client_id) ON DELETE CASCADE,
            building_id varchar(64) NOT NULL REFERENCES buildings(building_id),
            PRIMARY KEY (client_id, building_id)
        )""")
    op.execute("""
        CREATE TABLE exports (
            export_id uuid PRIMARY KEY,
            client_id varchar(64) NOT NULL REFERENCES export_clients(client_id),
            idempotency_key varchar(64) NOT NULL,
            request_hash char(64) NOT NULL,
            building_id varchar(64) NOT NULL REFERENCES buildings(building_id),
            metric varchar(16) NOT NULL,
            start_at timestamptz NOT NULL,
            end_at timestamptz NOT NULL,
            row_count integer NOT NULL,
            content_sha256 char(64) NOT NULL,
            content bytea NOT NULL,
            created_at timestamptz NOT NULL,
            CONSTRAINT uq_exports_client_key UNIQUE (client_id, idempotency_key),
            CONSTRAINT ck_exports_metric CHECK (metric IN ('power_kw','energy_kwh')),
            CONSTRAINT ck_exports_range_order CHECK (start_at < end_at),
            CONSTRAINT ck_exports_range_max_31d CHECK (end_at - start_at <= interval '31 days'),
            CONSTRAINT ck_exports_row_count_nonneg CHECK (row_count >= 0)
        )""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS exports")
    op.execute("DROP TABLE IF EXISTS export_client_scopes")
    op.execute("DROP TABLE IF EXISTS export_clients")
