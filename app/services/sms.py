"""SMS delivery boundary.

The real provider is intentionally not embedded in auth logic. Configure and
implement a provider adapter before using SMS authentication outside local
development.
"""

from __future__ import annotations

from app.core.config import Settings


class SmsDeliveryError(RuntimeError):
    pass


async def send_verification_code(
    *, phone_number: str, code: str, settings: Settings
) -> None:
    if settings.sms_provider == "dev" and settings.app_env in {"local", "test"}:
        return
    raise SmsDeliveryError("SMS provider is not configured")
