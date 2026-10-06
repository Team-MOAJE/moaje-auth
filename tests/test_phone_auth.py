import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import hash_pin, utc_now
from app.schemas.auth import PinResetRequest, RegisterRequest
from app.services import auth


SETTINGS = Settings(
    _env_file=None,
    APP_ENV="test",
    SECRET_KEY="phone-auth-test-secret",
    SMS_PROVIDER="dev",
    SMS_DEV_EXPOSE_CODE=True,
    SMS_OTP_EXPIRE_MINUTES=5,
    SMS_OTP_MAX_ATTEMPTS=2,
    PIN_MAX_ATTEMPTS=2,
    PIN_LOCK_MINUTES=30,
)


class PhoneAuthTests(unittest.IsolatedAsyncioTestCase):
    def test_phone_normalization(self):
        self.assertEqual(auth.normalize_phone_number("010-1234-5678"), "+821012345678")
        self.assertEqual(auth.normalize_phone_number("+821012345678"), "+821012345678")
        with self.assertRaises(ValueError):
            auth.normalize_phone_number("02-123-4567")

    def test_pin_is_six_digits_and_confirmation_must_match(self):
        base = {
            "verification_token": "x" * 40,
            "name": "테스트",
            "terms_agreed": True,
            "privacy_agreed": True,
            "terms_version": "v1",
            "privacy_version": "v1",
        }
        with self.assertRaises(ValidationError):
            RegisterRequest(**base, pin="12345", pin_confirm="12345")
        with self.assertRaises(ValidationError):
            RegisterRequest(**base, pin="123456", pin_confirm="654321")
        with self.assertRaises(ValidationError):
            PinResetRequest(
                verification_token="x" * 40,
                new_pin="123456",
                new_pin_confirm="654321",
            )

    async def test_sms_request_and_verification_are_one_time(self):
        db = AsyncMock()
        created = {}

        async def remember(_db, **kwargs):
            created.update(kwargs)

        with (
            patch.object(auth.auth_repository, "get_user_by_phone", new=AsyncMock(return_value=None)),
            patch.object(auth.auth_repository, "get_latest_sms_verification", new=AsyncMock(return_value=None)),
            patch.object(auth.auth_repository, "count_sms_verifications_since", new=AsyncMock(return_value=0)),
            patch.object(auth.auth_repository, "create_sms_verification", new=AsyncMock(side_effect=remember)),
            patch.object(auth.sms_service, "send_verification_code", new=AsyncMock()),
        ):
            requested = await auth.request_sms_verification(
                db,
                phone_number="01012345678",
                purpose="REGISTER",
                settings=SETTINGS,
            )

        self.assertRegex(requested.dev_code or "", r"^\d{6}$")
        verification = SimpleNamespace(
            verification_id=requested.verification_id,
            code_digest=created["code_digest"],
            failed_attempts=0,
            expires_at=utc_now().replace(tzinfo=None) + timedelta(minutes=5),
            verified_at=None,
            consumed_at=None,
            verification_token_hash=None,
        )
        with patch.object(
            auth.auth_repository,
            "get_sms_verification_for_update",
            new=AsyncMock(return_value=verification),
        ):
            verified = await auth.verify_sms_code(
                db,
                verification_id=requested.verification_id,
                code=requested.dev_code or "",
                settings=SETTINGS,
            )
            self.assertGreater(len(verified.verification_token), 32)
            with self.assertRaises(auth.SmsVerificationError):
                await auth.verify_sms_code(
                    db,
                    verification_id=requested.verification_id,
                    code=requested.dev_code or "",
                    settings=SETTINGS,
                )

    async def test_pin_attempts_are_locked_server_side(self):
        db = AsyncMock()
        credential = SimpleNamespace(
            pin_hash=hash_pin("123456"),
            failed_attempts=0,
            locked_until=None,
        )
        user = SimpleNamespace(pin_credential=credential)
        with self.assertRaises(auth.InvalidCredentialsError):
            await auth._verify_user_pin(
                db, user=user, pin="000000", settings=SETTINGS
            )
        with self.assertRaises(auth.PinLockedError):
            await auth._verify_user_pin(
                db, user=user, pin="000000", settings=SETTINGS
            )
        self.assertEqual(credential.failed_attempts, 2)
        self.assertIsNotNone(credential.locked_until)


if __name__ == "__main__":
    unittest.main()
