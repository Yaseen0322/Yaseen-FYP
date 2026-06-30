"""Add alert dedupe key

Revision ID: 0002_alert_dedupe_key
Revises: 0001_initial_schema
Create Date: 2026-04-06 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_alert_dedupe_key"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("alerts")}
    indexes = {index["name"] for index in inspector.get_indexes("alerts")}

    with op.batch_alter_table("alerts") as batch_op:
        if "dedupe_key" not in columns:
            batch_op.add_column(sa.Column("dedupe_key", sa.String(length=255), nullable=True))

        if "ux_alerts_dedupe_key" not in indexes:
            batch_op.create_index("ux_alerts_dedupe_key", ["dedupe_key"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("alerts")}
    indexes = {index["name"] for index in inspector.get_indexes("alerts")}

    with op.batch_alter_table("alerts") as batch_op:
        if "ux_alerts_dedupe_key" in indexes:
            batch_op.drop_index("ux_alerts_dedupe_key")
        if "dedupe_key" in columns:
            batch_op.drop_column("dedupe_key")
