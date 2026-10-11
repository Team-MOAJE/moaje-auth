import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import hash_pin, verify_pin
from app.main import app
from app.schemas.auth import PinChangeRequest, RegisterRequest
from app.services import auth


SETTINGS = Settings(
    APP_ENV="test",
    SECRET_KEY="phone-auth-test-secret",
    PIN_MAX_ATTEMPTS=2,
    PIN_LOCK_MINUTES=30,
)


class PhoneAuthTests(unittest.IsolatedAsyncioTestCase):
    def test_openapi_uses_phone_and_pin_without_sms_routes(self):
        paths = app.openapi()["paths"]
        self.assertNotIn("/api/auth/sms/request", paths)
        self.assertNotIn("/api/auth/sms/verify", paths)
        self.assertEqual(
            paths["/api/auth/pin/change"]["post"]["security"],
            [{"HTTPBearer": []}],
        )

    def test_phone_normalization(self):
        self.assertEqual(auth.normalize_phone_number("010-1234-5678"), "+821012345678")
        self.assertEqual(auth.normalize_phone_number("+821012345678"), "+821012345678")
        with self.assertRaises(auth.InvalidPhoneNumberError):
            auth.normalize_phone_number("02-123-4567")

    def test_pin_is_six_digits_and_confirmation_must_match(self):
        base = {
            "phone_number": "01012345678",
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
            PinChangeRequest(
                current_pin="123456",
                new_pin="654321",
                new_pin_confirm="111111",
            )

    async def test_registration_checks_normalized_phone_without_sms(self):
        db = AsyncMock()
        with patch.object(
            auth.auth_repository,
            "get_user_by_phone",
            new=AsyncMock(return_value=SimpleNamespace(user_id=1)),
        ) as lookup:
            with self.assertRaises(auth.DuplicateUserError):
                await auth.register_phone_user(
                    db,
                    phone_number="010-1234-5678",
                    name="테스트",
                    pin="123456",
                    terms_version="v1",
                    privacy_version="v1",
                )

        self.assertEqual(lookup.await_args_list[0].args[1], "+821012345678")

    async def test_login_uses_phone_and_pin_without_sms(self):
        db = AsyncMock()
        credential = SimpleNamespace(
            pin_hash=hash_pin("123456"),
            failed_attempts=0,
            locked_until=None,
        )
        user = SimpleNamespace(
            user_id=123,
            is_active=1,
            onboarding_completed=False,
            pin_credential=credential,
        )
        issued = auth.IssuedTokens("access", "refresh", 1800)
        with (
            patch.object(
                auth.auth_repository,
                "get_user_by_phone",
                new=AsyncMock(return_value=user),
            ) as lookup,
            patch.object(auth, "issue_tokens", new=AsyncMock(return_value=issued)),
        ):
            tokens, onboarding_completed = await auth.login_phone_user(
                db,
                phone_number="010-1234-5678",
                pin="123456",
                settings=SETTINGS,
            )

        self.assertEqual(lookup.await_args_list[0].args[1], "+821012345678")
        self.assertEqual(tokens, issued)
        self.assertFalse(onboarding_completed)

    async def test_pin_change_verifies_current_pin_and_revokes_sessions(self):
        db = AsyncMock()
        credential = SimpleNamespace(
            pin_hash=hash_pin("123456"),
            failed_attempts=0,
            locked_until=None,
            last_changed_at=None,
        )
        user = SimpleNamespace(user_id=123, is_active=1, pin_credential=credential)
        revoke = AsyncMock()
        with (
            patch.object(
                auth.auth_repository,
                "get_user_by_id",
                new=AsyncMock(return_value=user),
            ),
            patch.object(
                auth.auth_repository,
                "revoke_user_refresh_tokens",
                new=revoke,
            ),
        ):
            await auth.change_pin(
                db,
                user_id=123,
                current_pin="123456",
                new_pin="654321",
                settings=SETTINGS,
            )

        self.assertTrue(verify_pin("654321", credential.pin_hash))
        revoke.assert_awaited_once_with(db, 123)

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
