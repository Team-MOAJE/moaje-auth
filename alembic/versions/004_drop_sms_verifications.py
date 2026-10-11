"""Drop unused SMS verification storage.

Revision ID: 004_drop_sms_verifications
Revises: 003_phone_auth_flow
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "004_drop_sms_verifications"
down_revision = "003_phone_auth_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("sms_verifications")


def downgrade() -> None:
    op.create_table(
        "sms_verifications",
        sa.Column("verification_id", sa.String(64), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("code_digest", sa.String(64), nullable=False),
        sa.Column("verification_token_hash", sa.String(64), nullable=True),
        sa.Column("failed_attempts", mysql.INTEGER(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("verification_id", name=op.f("pk_sms_verifications")),
        sa.UniqueConstraint("verification_token_hash", name="uq_sms_verifications_token_hash"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_sms_verifications_phone_purpose",
        "sms_verifications",
        ["phone_number", "purpose"],
    )
    op.create_index(
        "ix_sms_verifications_expires_at",
        "sms_verifications",
        ["expires_at"],
    )
