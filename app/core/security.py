"""PIN과 토큰 처리를 위한 모듈"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import Settings, get_settings


__all__ = [
    "TokenConfigurationError",
    "TokenValidationError",
    "create_access_token",
    "decode_token",
    "generate_refresh_token",
    "hash_pin",
    "hash_token",
    "utc_now",
    "validate_access_token",
    "verify_pin",
]


class TokenValidationError(ValueError):
    """JWT 검증 실패."""


class TokenConfigurationError(ValueError):
    """JWT 설정 오류."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_pin(pin: str, pin_hash: str) -> bool:
    return bcrypt.checkpw(pin.encode("utf-8"), pin_hash.encode("utf-8"))


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalized_algorithm(settings: Settings) -> str:
    return settings.algorithm.upper()


def _is_symmetric_algorithm(algorithm: str) -> bool:
    return algorithm.startswith("HS")


def _is_asymmetric_algorithm(algorithm: str) -> bool:
    return algorithm.startswith(("RS", "ES", "PS"))


def _get_signing_key(settings: Settings) -> str:
    algorithm = _normalized_algorithm(settings)
    if _is_symmetric_algorithm(algorithm):
        return settings.secret_key
    if _is_asymmetric_algorithm(algorithm):
        if not settings.jwt_private_key:
            raise TokenConfigurationError("JWT_PRIVATE_KEY is required for asymmetric JWT signing")
        return settings.jwt_private_key
    raise TokenConfigurationError(f"Unsupported JWT algorithm: {settings.algorithm}")


def _get_verification_key(settings: Settings) -> str:
    algorithm = _normalized_algorithm(settings)
    if _is_symmetric_algorithm(algorithm):
        return settings.secret_key
    if _is_asymmetric_algorithm(algorithm):
        if not settings.jwt_public_key:
            raise TokenConfigurationError("JWT_PUBLIC_KEY is required for asymmetric JWT verification")
        return settings.jwt_public_key
    raise TokenConfigurationError(f"Unsupported JWT algorithm: {settings.algorithm}")


def create_access_token(
    user_id: int | str,
    *,
    settings: Settings | None = None,
    transaction_id: str | None = None,
) -> tuple[str, int]:
    settings = settings or get_settings()
    issued_at = utc_now()
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "typ": "access",
        "jti": secrets.token_urlsafe(16),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.jwt_issuer,
    }
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience
    if transaction_id:
        payload["transaction_id"] = transaction_id

    token = jwt.encode(payload, _get_signing_key(settings), algorithm=_normalized_algorithm(settings))
    expires_in = int((expires_at - issued_at).total_seconds())
    return token, expires_in


def decode_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    try:
        decode_options: dict[str, Any] = {"verify_aud": bool(settings.jwt_audience)}
        return jwt.decode(
            token,
            _get_verification_key(settings),
            algorithms=[_normalized_algorithm(settings)],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options=decode_options,
        )
    except JWTError as exc:
        raise TokenValidationError("Invalid token") from exc


def validate_access_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    payload = decode_token(token, settings=settings)
    if payload.get("typ") != "access":
        raise TokenValidationError("Invalid token type")
    if not payload.get("sub"):
        raise TokenValidationError("Missing subject")
    return payload
