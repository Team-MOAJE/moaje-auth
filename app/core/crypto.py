"""암복호화 모듈"""

from __future__ import annotations

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings, get_settings


class EncryptionConfigurationError(ValueError):
    """암호화 설정 오류."""


class DecryptionError(ValueError):
    """복호화 실패."""


def _decode_master_key(settings: Settings) -> bytes:
    raw_key = settings.aes_master_key
    if raw_key == "change-me":
        raise EncryptionConfigurationError("AES_MASTER_KEY must be configured")

    try:
        key = base64.urlsafe_b64decode(raw_key)
    except ValueError as exc:
        raise EncryptionConfigurationError(
            "AES_MASTER_KEY must be URL-safe base64"
        ) from exc

    if len(key) != 32:
        raise EncryptionConfigurationError("AES_MASTER_KEY must decode to 32 bytes")
    return key


def encrypt_text(plaintext: str, *, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    key = _decode_master_key(settings)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    token = nonce + ciphertext
    return base64.urlsafe_b64encode(token).decode("utf-8")


def decrypt_text(encrypted_text: str, *, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    key = _decode_master_key(settings)

    try:
        token = base64.urlsafe_b64decode(encrypted_text)
        nonce = token[:12]
        ciphertext = token[12:]
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    except (ValueError, InvalidTag) as exc:
        raise DecryptionError("Failed to decrypt value") from exc

    return plaintext.decode("utf-8")
