"""Add user onboarding completion status.

Revision ID: 002_add_onboarding_completed
Revises: 001_create_auth_schema
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "002_add_onboarding_completed"
down_revision = "001_create_auth_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
