import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.api.auth import create_account_token
from app.core.config import Settings
from app.core.security import create_access_token
from app.schemas.auth import CreateAccountTokenRequest


SETTINGS = Settings(SECRET_KEY="account-token-authorization-test-secret")


class AccountTokenAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_account_token_for_another_user(self):
        token, _ = create_access_token("123", settings=SETTINGS)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        service = AsyncMock()

        with patch("app.core.security.get_settings", return_value=SETTINGS), patch(
            "app.api.auth.auth_service.create_account_token", new=service
        ):
            response = await create_account_token(
                Request({"type": "http", "headers": []}),
                CreateAccountTokenRequest(user_id=456, account_number="100200300"),
                credentials,
                AsyncMock(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(bytes(response.body).decode("utf-8"))["code"],
            "AUTH-403-001",
        )
        service.assert_not_awaited()

    async def test_uses_authenticated_subject_for_matching_user(self):
        token, _ = create_access_token("123", settings=SETTINGS)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        service = AsyncMock(
            return_value=SimpleNamespace(account_token="acct_test", user_id=123)
        )

        with patch("app.core.security.get_settings", return_value=SETTINGS), patch(
            "app.api.auth.auth_service.create_account_token", new=service
        ):
            response = await create_account_token(
                Request({"type": "http", "headers": []}),
                CreateAccountTokenRequest(user_id=123, account_number="100200300"),
                credentials,
                AsyncMock(),
            )

        self.assertEqual(response.status_code, 200)
        service.assert_awaited_once()
        self.assertEqual(service.await_args_list[0].kwargs["user_id"], 123)


if __name__ == "__main__":
    unittest.main()
