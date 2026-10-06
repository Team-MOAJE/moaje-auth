"""Add phone-based authentication data.

Revision ID: 003_phone_auth_flow
Revises: 002_add_onboarding_completed
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "003_phone_auth_flow"
down_revision = "002_add_onboarding_completed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.add_column("users", sa.Column("phone_number", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("terms_version", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("privacy_version", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("terms_agreed_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint("uq_users_phone_number", "users", ["phone_number"])

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
    op.create_index("ix_sms_verifications_expires_at", "sms_verifications", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_sms_verifications_expires_at", table_name="sms_verifications")
    op.drop_index("ix_sms_verifications_phone_purpose", table_name="sms_verifications")
    op.drop_table("sms_verifications")
    op.drop_constraint("uq_users_phone_number", "users", type_="unique")
    op.drop_column("users", "terms_agreed_at")
    op.drop_column("users", "privacy_version")
    op.drop_column("users", "terms_version")
    op.drop_column("users", "name")
    op.drop_column("users", "phone_number")
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
