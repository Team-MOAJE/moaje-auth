"""Auth 비즈니스 로직 계층 ... """

from __future__ import annotations

import re
import secrets
import time
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
    hash_pin,
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


class DuplicateUserError(AuthError):
    default_message = "이미 가입된 사용자입니다."


class UserNotFoundError(AuthError):
    default_message = "사용자를 찾을 수 없습니다."


class InvalidCredentialsError(AuthError):
    default_message = "전화번호 또는 PIN이 올바르지 않습니다."


class InvalidPhoneNumberError(AuthError):
    default_message = "휴대전화 번호 형식이 올바르지 않습니다."


class InvalidRefreshTokenError(AuthError):
    default_message = "Refresh Token이 유효하지 않습니다."


class AccountTokenError(AuthError):
    default_message = "계좌 토큰 처리 중 오류가 발생했습니다."


class PinLockedError(AuthError):
    default_message = "간편 비밀번호 인증이 잠겼습니다."


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


@dataclass(frozen=True)
class RegisteredUser:
    user_id: int
    phone_number: str
    name: str
    onboarding_completed: bool
    tokens: IssuedTokens


def generate_user_id() -> int:
    # 임시 Snowflake 대체값
    return (int(time.time() * 1000) << 16) | secrets.randbelow(1 << 16)


def normalize_phone_number(value: str) -> str:
    compact = re.sub(r"[\s()-]", "", value)
    if re.fullmatch(r"010\d{8}", compact):
        return "+82" + compact[1:]
    if re.fullmatch(r"\+8210\d{8}", compact):
        return compact
    raise InvalidPhoneNumberError()


def parse_user_id(value: str) -> int:
    if not value or len(value) > 19 or not value.isascii() or not value.isdecimal():
        raise ValueError("Invalid user ID")
    user_id = int(value)
    if not 0 < user_id <= (1 << 63) - 1:
        raise ValueError("Invalid user ID")
    return user_id


async def complete_onboarding(db: AsyncSession, *, user_id: int) -> None:
    user = await auth_repository.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise UserNotFoundError()
    user.onboarding_completed = True
    await db.commit()


async def register_with_pin(
    db: AsyncSession, *, email: str, pin: str
) -> tuple[int, str, bool]:
    existing_user = await auth_repository.get_user_by_email(db, email)
    if existing_user:
        raise DuplicateUserError("Email already registered")

    try:
        user = await auth_repository.create_pin_user(
            db,
            user_id=generate_user_id(),
            email=email,
            pin_hash=hash_pin(pin),
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateUserError("Email already registered") from exc

    return user.user_id, user.email or "", bool(user.is_active)


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


async def register_phone_user(
    db: AsyncSession,
    *,
    phone_number: str,
    name: str,
    pin: str,
    terms_version: str,
    privacy_version: str,
    email: str | None = None,
    device_info: str | None = None,
) -> RegisteredUser:
    normalized_phone = normalize_phone_number(phone_number)
    if await auth_repository.get_user_by_phone(db, normalized_phone):
        raise DuplicateUserError("이미 가입된 번호입니다. 로그인해 주세요.")
    try:
        user = await auth_repository.create_phone_user(
            db,
            user_id=generate_user_id(),
            phone_number=normalized_phone,
            name=name.strip(),
            email=email,
            pin_hash=hash_pin(pin),
            terms_version=terms_version,
            privacy_version=privacy_version,
            terms_agreed_at=utc_now().replace(tzinfo=None),
        )
        tokens = await issue_tokens(
            db, user_id=user.user_id, device_info=device_info
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateUserError("이미 가입된 번호입니다. 로그인해 주세요.") from exc
    return RegisteredUser(
        user_id=user.user_id,
        phone_number=normalized_phone,
        name=user.name or "",
        onboarding_completed=False,
        tokens=tokens,
    )


def _pin_is_locked(credential: object) -> bool:
    locked_until = getattr(credential, "locked_until", None)
    return bool(locked_until and locked_until > utc_now().replace(tzinfo=None))


async def _verify_user_pin(
    db: AsyncSession,
    *,
    user: object,
    pin: str,
    settings: Settings,
) -> None:
    credential = getattr(user, "pin_credential", None)
    if credential is None:
        raise InvalidCredentialsError("간편 비밀번호가 설정되지 않았습니다.")
    if _pin_is_locked(credential):
        raise PinLockedError("잠금 시간이 지난 후 다시 시도해 주세요.")
    if not verify_pin(pin, credential.pin_hash):
        credential.failed_attempts += 1
        if credential.failed_attempts >= settings.pin_max_attempts:
            credential.locked_until = (
                utc_now() + timedelta(minutes=settings.pin_lock_minutes)
            ).replace(tzinfo=None)
        await db.commit()
        if _pin_is_locked(credential):
            raise PinLockedError("잠금 시간이 지난 후 다시 시도해 주세요.")
        raise InvalidCredentialsError("간편 비밀번호가 올바르지 않습니다.")
    credential.failed_attempts = 0
    credential.locked_until = None


async def login_phone_user(
    db: AsyncSession,
    *,
    phone_number: str,
    pin: str,
    device_info: str | None = None,
    settings: Settings | None = None,
) -> tuple[IssuedTokens, bool]:
    settings = settings or get_settings()
    normalized_phone = normalize_phone_number(phone_number)
    user = await auth_repository.get_user_by_phone(db, normalized_phone)
    if not user or not user.is_active:
        await db.rollback()
        raise InvalidCredentialsError()
    await _verify_user_pin(db, user=user, pin=pin, settings=settings)
    tokens = await issue_tokens(
        db, user_id=user.user_id, device_info=device_info, settings=settings
    )
    await db.commit()
    return tokens, bool(user.onboarding_completed)


async def unlock_session(
    db: AsyncSession,
    *,
    refresh_token: str,
    pin: str,
    settings: Settings | None = None,
) -> tuple[IssuedTokens, bool]:
    settings = settings or get_settings()
    stored = await auth_repository.get_refresh_token_by_hash(
        db, hash_token(refresh_token)
    )
    now = utc_now().replace(tzinfo=None)
    if not stored or stored.is_revoked or stored.expires_at <= now:
        raise InvalidRefreshTokenError()
    user = await auth_repository.get_user_by_id(db, stored.user_id)
    if not user or not user.is_active:
        raise InvalidCredentialsError()
    await _verify_user_pin(db, user=user, pin=pin, settings=settings)
    await auth_repository.revoke_refresh_token(db, stored)
    tokens = await issue_tokens(
        db,
        user_id=user.user_id,
        device_info=stored.device_info,
        settings=settings,
    )
    await db.commit()
    return tokens, bool(user.onboarding_completed)


async def change_pin(
    db: AsyncSession,
    *,
    user_id: int,
    current_pin: str,
    new_pin: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    user = await auth_repository.get_user_by_id(db, user_id)
    if not user or not user.is_active or not user.pin_credential:
        raise UserNotFoundError()
    await _verify_user_pin(db, user=user, pin=current_pin, settings=settings)
    user.pin_credential.pin_hash = hash_pin(new_pin)
    user.pin_credential.failed_attempts = 0
    user.pin_credential.locked_until = None
    user.pin_credential.last_changed_at = utc_now().replace(tzinfo=None)
    await auth_repository.revoke_user_refresh_tokens(db, user.user_id)
    await db.commit()


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

    user = await auth_repository.get_user_by_id(db, stored_token.user_id)
    if not user or not user.is_active:
        raise InvalidRefreshTokenError("User is unavailable")

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


async def is_mfa_required(db: AsyncSession, *, user_id: int) -> bool:
    mfa_config = await auth_repository.get_mfa_config_by_user_id(db, user_id)
    return bool(mfa_config and mfa_config.is_enabled)


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
