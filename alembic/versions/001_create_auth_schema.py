"""create auth schema

Revision ID: 001_create_auth_schema
Revises:
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "001_create_auth_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_active", mysql.TINYINT(display_width=1), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name="uq_users_email"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )

    op.create_table(
        "oauth_accounts",
        sa.Column("oauth_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_uid", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_oauth_accounts_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("oauth_id", name=op.f("pk_oauth_accounts")),
        sa.UniqueConstraint("provider", "provider_uid", name="uq_oauth_accounts_provider_provider_uid"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])

    op.create_table(
        "pin_credentials",
        sa.Column("pin_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("pin_hash", sa.String(length=255), nullable=False),
        sa.Column("failed_attempts", mysql.INTEGER(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_pin_credentials_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pin_id", name=op.f("pk_pin_credentials")),
        sa.UniqueConstraint("user_id", name="uq_pin_credentials_user_id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("token_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=512), nullable=False),
        sa.Column("device_info", sa.String(length=500), nullable=True),
        sa.Column("issued_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", mysql.TINYINT(display_width=1), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "webauthn_credentials",
        sa.Column("credential_id", sa.String(length=512), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("public_key_enc", sa.Text(), nullable=False),
        sa.Column("aaguid", sa.String(length=36), nullable=True),
        sa.Column("sign_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_webauthn_credentials_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("credential_id", name=op.f("pk_webauthn_credentials")),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_webauthn_credentials_user_id", "webauthn_credentials", ["user_id"])

    op.create_table(
        "mfa_configs",
        sa.Column("mfa_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("totp_secret_enc", sa.String(length=512), nullable=False),
        sa.Column("key_version", mysql.INTEGER(), server_default="1", nullable=False),
        sa.Column("is_enabled", mysql.TINYINT(display_width=1), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_mfa_configs_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mfa_id", name=op.f("pk_mfa_configs")),
        sa.UniqueConstraint("user_id", name="uq_mfa_configs_user_id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )

    op.create_table(
        "account_token_mappings",
        sa.Column("mapping_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("account_token", sa.String(length=255), nullable=False),
        sa.Column("encrypted_account_no", sa.String(length=512), nullable=False),
        sa.Column("key_version", mysql.INTEGER(), server_default="1", nullable=False),
        sa.Column("is_active", mysql.TINYINT(display_width=1), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_account_token_mappings_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mapping_id", name=op.f("pk_account_token_mappings")),
        sa.UniqueConstraint("account_token", name="uq_account_token_mappings_account_token"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_account_token_mappings_user_id", "account_token_mappings", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_account_token_mappings_user_id", table_name="account_token_mappings")
    op.drop_table("account_token_mappings")
    op.drop_table("mfa_configs")
    op.drop_index("ix_webauthn_credentials_user_id", table_name="webauthn_credentials")
    op.drop_table("webauthn_credentials")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("pin_credentials")
    op.drop_index("ix_oauth_accounts_user_id", table_name="oauth_accounts")
    op.drop_table("oauth_accounts")
    op.drop_table("users")
