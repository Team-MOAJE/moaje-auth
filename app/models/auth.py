"""Auth MySQL 스키마 SQLAlchemy ORM 모델"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[int] = mapped_column(TINYINT(1), nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    pin_credential: Mapped["PinCredential | None"] = relationship(
        "PinCredential",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    webauthn_credentials: Mapped[list["WebAuthnCredential"]] = relationship(
        "WebAuthnCredential",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    mfa_configs: Mapped[list["MfaConfig"]] = relationship(
        "MfaConfig",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    account_token_mappings: Mapped[list["AccountTokenMapping"]] = relationship(
        "AccountTokenMapping",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_uid", name="uq_oauth_accounts_provider_provider_uid"),
        Index("ix_oauth_accounts_user_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    oauth_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_uid: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")


class PinCredential(Base):
    __tablename__ = "pin_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_pin_credentials_user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    pin_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(INTEGER, nullable=False, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship("User", back_populates="pin_credential")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    token_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    device_info: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[int] = mapped_column(TINYINT(1), nullable=False, server_default="0")

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"
    __table_args__ = (
        Index("ix_webauthn_credentials_user_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    credential_id: Mapped[str] = mapped_column(String(512), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    public_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    aaguid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="webauthn_credentials")


class MfaConfig(Base):
    __tablename__ = "mfa_configs"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_mfa_configs_user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    mfa_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    totp_secret_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    key_version: Mapped[int] = mapped_column(INTEGER, nullable=False, server_default="1")
    is_enabled: Mapped[int] = mapped_column(TINYINT(1), nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="mfa_configs")


class AccountTokenMapping(Base):
    __tablename__ = "account_token_mappings"
    __table_args__ = (
        UniqueConstraint("account_token", name="uq_account_token_mappings_account_token"),
        Index("ix_account_token_mappings_user_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    mapping_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    account_token: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_account_no: Mapped[str] = mapped_column(String(512), nullable=False)
    key_version: Mapped[int] = mapped_column(INTEGER, nullable=False, server_default="1")
    is_active: Mapped[int] = mapped_column(TINYINT(1), nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship("User", back_populates="account_token_mappings")
