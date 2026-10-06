"""Auth 모델 데이터베이스 조회 계층"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import (
    AccountTokenMapping,
    MfaConfig,
    PinCredential,
    RefreshToken,
    SmsVerification,
    User,
)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).options(selectinload(User.pin_credential)).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).options(selectinload(User.pin_credential)).where(User.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> User | None:
    stmt = (
        select(User)
        .options(selectinload(User.pin_credential))
        .where(User.phone_number == phone_number)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_pin_user(
    db: AsyncSession,
    *,
    user_id: int,
    email: str,
    pin_hash: str,
) -> User:
    user = User(user_id=user_id, email=email, is_active=1)
    user.pin_credential = PinCredential(pin_hash=pin_hash)
    db.add(user)
    await db.flush()
    return user


async def create_phone_user(
    db: AsyncSession,
    *,
    user_id: int,
    phone_number: str,
    name: str,
    pin_hash: str,
    terms_version: str,
    privacy_version: str,
    terms_agreed_at: datetime,
    email: str | None = None,
) -> User:
    user = User(
        user_id=user_id,
        phone_number=phone_number,
        name=name,
        email=email,
        is_active=1,
        onboarding_completed=False,
        terms_version=terms_version,
        privacy_version=privacy_version,
        terms_agreed_at=terms_agreed_at,
    )
    user.pin_credential = PinCredential(pin_hash=pin_hash)
    db.add(user)
    await db.flush()
    return user


async def create_sms_verification(
    db: AsyncSession,
    *,
    verification_id: str,
    phone_number: str,
    purpose: str,
    code_digest: str,
    expires_at: datetime,
) -> SmsVerification:
    verification = SmsVerification(
        verification_id=verification_id,
        phone_number=phone_number,
        purpose=purpose,
        code_digest=code_digest,
        expires_at=expires_at,
    )
    db.add(verification)
    await db.flush()
    return verification


async def get_sms_verification_for_update(
    db: AsyncSession, verification_id: str
) -> SmsVerification | None:
    stmt = (
        select(SmsVerification)
        .where(SmsVerification.verification_id == verification_id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_sms_verification_by_token_for_update(
    db: AsyncSession, token_hash: str
) -> SmsVerification | None:
    stmt = (
        select(SmsVerification)
        .where(SmsVerification.verification_token_hash == token_hash)
        .with_for_update()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_sms_verification(
    db: AsyncSession, *, phone_number: str, purpose: str
) -> SmsVerification | None:
    stmt = (
        select(SmsVerification)
        .where(
            SmsVerification.phone_number == phone_number,
            SmsVerification.purpose == purpose,
        )
        .order_by(SmsVerification.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def count_sms_verifications_since(
    db: AsyncSession, *, phone_number: str, since: datetime
) -> int:
    stmt = select(func.count()).select_from(SmsVerification).where(
        SmsVerification.phone_number == phone_number,
        SmsVerification.created_at >= since,
    )
    result = await db.execute(stmt)
    return int(result.scalar_one())


async def create_refresh_token(
    db: AsyncSession,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    device_info: str | None = None,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
        is_revoked=0,
    )
    db.add(refresh_token)
    await db.flush()
    return refresh_token


async def get_refresh_token_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, refresh_token: RefreshToken) -> None:
    refresh_token.is_revoked = 1
    await db.flush()


async def revoke_user_refresh_tokens(db: AsyncSession, user_id: int) -> int:
    stmt = update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == 0).values(is_revoked=1)
    result = cast(CursorResult, await db.execute(stmt))
    return result.rowcount or 0


async def create_account_token_mapping(
    db: AsyncSession,
    *,
    user_id: int,
    account_token: str,
    encrypted_account_no: str,
    key_version: int,
) -> AccountTokenMapping:
    mapping = AccountTokenMapping(
        user_id=user_id,
        account_token=account_token,
        encrypted_account_no=encrypted_account_no,
        key_version=key_version,
        is_active=1,
    )
    db.add(mapping)
    await db.flush()
    return mapping


async def get_mfa_config_by_user_id(db: AsyncSession, user_id: int) -> MfaConfig | None:
    stmt = select(MfaConfig).where(MfaConfig.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_account_token_mapping(
    db: AsyncSession,
    account_token: str,
) -> AccountTokenMapping | None:
    stmt = select(AccountTokenMapping).where(
        AccountTokenMapping.account_token == account_token,
        AccountTokenMapping.is_active == 1,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
