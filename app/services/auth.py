"""Auth 비즈니스 로직 계층 ... """

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.security import (
    TokenValidationError,
    create_access_token,
    generate_refresh_token,
    hash_token,
    utc_now,
    verify_pin,
)
from app.core.security import validate_access_token as validate_jwt_access_token
from app.repositories import auth as auth_repository


## ---- 에러 처리 관련 ... 추후 확장 필요. 지금은 임시
class AuthError(ValueError):
    default_message = "Auth 처리 중 오류가 발생했습니다."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class UserNotFoundError(AuthError):
    default_message = "사용자를 찾을 수 없습니다."


class InvalidCredentialsError(AuthError):
    default_message = "이메일 또는 PIN이 올바르지 않습니다."


class InvalidRefreshTokenError(AuthError):
    default_message = "Refresh Token이 유효하지 않습니다."


class AccountTokenError(AuthError):
    default_message = "계좌 토큰 처리 중 오류가 발생했습니다."


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass(frozen=True)
class ValidatedAccessToken:
    is_valid: bool
    user_id: str = ""
    expires_at: int = 0


@dataclass(frozen=True)
class CreatedAccountToken:
    account_token: str
    user_id: int


@dataclass(frozen=True)
class ValidatedAccountToken:
    is_valid: bool
    user_id: int | None = None
    is_active: bool = False


async def issue_tokens(
    db: AsyncSession,
    *,
    user_id: int,
    device_info: str | None = None,
    settings: Settings | None = None,
) -> IssuedTokens:
    settings = settings or get_settings()
    access_token, expires_in = create_access_token(user_id, settings=settings)
    refresh_token = generate_refresh_token()
    refresh_expires_at = utc_now() + timedelta(days=settings.refresh_token_expire_days)

    await auth_repository.create_refresh_token(
        db,
        user_id=user_id,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires_at.replace(tzinfo=None),
        device_info=device_info,
    )
    return IssuedTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


async def login_with_pin(
    db: AsyncSession,
    *,
    email: str,
    pin: str,
    device_info: str | None = None,
) -> IssuedTokens:
    user = await auth_repository.get_user_by_email(db, email)
    if not user or not user.pin_credential or not bool(user.is_active):
        raise InvalidCredentialsError("Invalid email or PIN")
    if not verify_pin(pin, user.pin_credential.pin_hash):
        raise InvalidCredentialsError("Invalid email or PIN")

    try:
        tokens = await issue_tokens(db, user_id=user.user_id, device_info=device_info)
        await db.commit()
        return tokens
    except IntegrityError:
        await db.rollback()
        raise


async def rotate_refresh_token(db: AsyncSession, *, refresh_token: str) -> IssuedTokens:
    token_hash = hash_token(refresh_token)
    stored_token = await auth_repository.get_refresh_token_by_hash(db, token_hash)
    now = utc_now().replace(tzinfo=None)

    if (
        not stored_token
        or bool(stored_token.is_revoked)
        or stored_token.expires_at <= now
    ):
        raise InvalidRefreshTokenError("Invalid refresh token")

    await auth_repository.revoke_refresh_token(db, stored_token)
    try:
        tokens = await issue_tokens(
            db,
            user_id=stored_token.user_id,
            device_info=stored_token.device_info,
        )
        await db.commit()
        return tokens
    except IntegrityError:
        await db.rollback()
        raise


async def logout(
    db: AsyncSession,
    *,
    refresh_token: str | None,
    all_devices: bool = False,
) -> None:
    if all_devices:
        if not refresh_token:
            raise InvalidRefreshTokenError(
                "Refresh token is required for all-devices logout"
            )
        stored_token = await auth_repository.get_refresh_token_by_hash(
            db,
            hash_token(refresh_token),
        )
        if not stored_token:
            raise InvalidRefreshTokenError("Invalid refresh token")
        await auth_repository.revoke_user_refresh_tokens(db, stored_token.user_id)
        await db.commit()
        return

    if not refresh_token:
        raise InvalidRefreshTokenError("Refresh token is required")

    stored_token = await auth_repository.get_refresh_token_by_hash(
        db,
        hash_token(refresh_token),
    )
    if not stored_token:
        raise InvalidRefreshTokenError("Invalid refresh token")

    await auth_repository.revoke_refresh_token(db, stored_token)
    await db.commit()


def validate_access_token(access_token: str) -> ValidatedAccessToken:
    try:
        payload = validate_jwt_access_token(access_token)
    except TokenValidationError:
        return ValidatedAccessToken(is_valid=False)

    return ValidatedAccessToken(
        is_valid=True,
        user_id=str(payload["sub"]),
        expires_at=int(payload["exp"]) * 1000,
    )


def generate_account_token() -> str:
    return f"acct_{secrets.token_urlsafe(32)}"


async def create_account_token(
    db: AsyncSession,
    *,
    user_id: int,
    account_number: str,
) -> CreatedAccountToken:
    user = await auth_repository.get_user_by_id(db, user_id)
    if not user or not bool(user.is_active):
        raise UserNotFoundError("User not found")

    encrypted_account_no = encrypt_text(account_number)
    settings = get_settings()

    for _ in range(3):
        account_token = generate_account_token()
        try:
            await auth_repository.create_account_token_mapping(
                db,
                user_id=user_id,
                account_token=account_token,
                encrypted_account_no=encrypted_account_no,
                key_version=settings.key_version,
            )
            await db.commit()
            return CreatedAccountToken(account_token=account_token, user_id=user_id)
        except IntegrityError:
            await db.rollback()

    raise AccountTokenError("Failed to create account token")


async def resolve_account_number(db: AsyncSession, *, account_token: str) -> str | None:
    mapping = await auth_repository.get_account_token_mapping(db, account_token)
    if not mapping:
        return None
    return decrypt_text(mapping.encrypted_account_no)


async def validate_account_token(
    db: AsyncSession,
    *,
    account_token: str,
) -> ValidatedAccountToken:
    mapping = await auth_repository.get_account_token_mapping(db, account_token)
    if not mapping:
        return ValidatedAccountToken(is_valid=False)

    return ValidatedAccountToken(
        is_valid=True,
        user_id=mapping.user_id,
        is_active=bool(mapping.is_active),
    )
