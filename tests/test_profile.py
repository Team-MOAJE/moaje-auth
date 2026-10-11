import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import hash_pin
from app.main import app
from app.schemas.auth import UpdateProfileRequest
from app.services import auth


SETTINGS = Settings(
    APP_ENV="test",
    SECRET_KEY="profile-test-secret",
    PIN_MAX_ATTEMPTS=5,
    PIN_LOCK_MINUTES=30,
)


class ProfileTests(unittest.IsolatedAsyncioTestCase):
    def test_profile_routes_require_bearer(self):
        operations = app.openapi()["paths"]["/api/auth/me"]
        self.assertEqual(operations["patch"]["security"], [{"HTTPBearer": []}])
        self.assertEqual(operations["delete"]["security"], [{"HTTPBearer": []}])

    def test_profile_update_requires_a_field_and_valid_email(self):
        with self.assertRaises(ValidationError):
            UpdateProfileRequest()
        with self.assertRaises(ValidationError):
            UpdateProfileRequest(email="invalid")
        with self.assertRaises(ValidationError):
            UpdateProfileRequest(name="   ")
        self.assertIsNone(UpdateProfileRequest(email=None).email)

    async def test_update_profile_normalizes_email(self):
        db = AsyncMock()
        user = SimpleNamespace(
            user_id=123,
            is_active=1,
            name="기존 이름",
            email="old@example.com",
        )
        with (
            patch.object(
                auth.auth_repository,
                "get_user_by_id",
                new=AsyncMock(return_value=user),
            ),
            patch.object(
                auth.auth_repository,
                "get_user_by_email",
                new=AsyncMock(return_value=None),
            ),
        ):
            updated = await auth.update_profile(
                db,
                user_id=123,
                name=" 새 이름 ",
                email="NEW@EXAMPLE.COM",
                email_provided=True,
            )

        self.assertEqual(updated.name, "새 이름")
        self.assertEqual(updated.email, "new@example.com")
        db.commit.assert_awaited_once()

    async def test_withdraw_clears_identity_and_revokes_credentials(self):
        db = AsyncMock()
        user = SimpleNamespace(
            user_id=123,
            is_active=1,
            phone_number="+821012345678",
            email="test@example.com",
            name="테스트",
            pin_credential=SimpleNamespace(
                pin_hash=hash_pin("123456"),
                failed_attempts=0,
                locked_until=None,
            ),
        )
        revoke_refresh = AsyncMock()
        deactivate_accounts = AsyncMock()
        with (
            patch.object(
                auth.auth_repository,
                "get_user_by_id",
                new=AsyncMock(return_value=user),
            ),
            patch.object(
                auth.auth_repository,
                "revoke_user_refresh_tokens",
                new=revoke_refresh,
            ),
            patch.object(
                auth.auth_repository,
                "deactivate_user_account_tokens",
                new=deactivate_accounts,
            ),
        ):
            await auth.withdraw_user(
                db,
                user_id=123,
                current_pin="123456",
                settings=SETTINGS,
            )

        self.assertEqual(user.is_active, 0)
        self.assertIsNone(user.phone_number)
        self.assertIsNone(user.email)
        self.assertIsNone(user.name)
        revoke_refresh.assert_awaited_once_with(db, 123)
        deactivate_accounts.assert_awaited_once_with(db, 123)
        db.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
