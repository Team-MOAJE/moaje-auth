import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import grpc
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.core import config

SETTINGS = config.Settings(_env_file=None, SECRET_KEY="onboarding-test-secret", WORK_SERVICE_TOKEN="work-test-token")
with patch.object(config, "get_settings", return_value=SETTINGS):
    from app.api.auth import current_user
    from app.main import app
    from app.rpc import service as rpc
    from app.services import auth
from app.core.security import create_access_token
from app.rpc.proto import auth_service_pb2 as pb


class RpcError(Exception):
    def __init__(self, code):
        self.code = code


class Context:
    def __init__(self, token="work-test-token"):
        self.token = token

    def invocation_metadata(self):
        return [("authorization", f"Bearer {self.token}")]

    async def abort(self, code, detail):
        raise RpcError(code)


class OnboardingTests(unittest.IsolatedAsyncioTestCase):
    async def test_me_uses_signed_subject(self):
        token, _ = create_access_token("123", settings=SETTINGS)
        request = Request({"type": "http", "headers": [(b"x-user-id", b"999")]})
        user = SimpleNamespace(user_id=123, is_active=1, onboarding_completed=False)
        with patch("app.core.security.get_settings", return_value=SETTINGS), patch(
            "app.api.auth.get_user_by_id", new=AsyncMock(return_value=user)
        ) as lookup:
            response = await current_user(request, HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), AsyncMock())
        self.assertEqual(lookup.call_args.args[1], 123)
        self.assertEqual(json.loads(response.body)["data"], {"user_id": "123", "onboarding_completed": False})

    async def test_me_rejects_missing_invalid_and_expired_token(self):
        expired = SETTINGS.model_copy(update={"access_token_expire_minutes": -1})
        token, _ = create_access_token("123", settings=expired)
        for credentials in [None, HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid"), HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)]:
            with patch("app.core.security.get_settings", return_value=SETTINGS), self.assertRaises(HTTPException) as caught:
                await current_user(Request({"type": "http", "headers": []}), credentials, AsyncMock())
            self.assertEqual(caught.exception.status_code, 401)

    async def test_completion_is_idempotent(self):
        user = SimpleNamespace(is_active=1, onboarding_completed=False)
        db = AsyncMock()
        with patch.object(auth.auth_repository, "get_user_by_id", new=AsyncMock(return_value=user)):
            await auth.complete_onboarding(db, user_id=123)
            await auth.complete_onboarding(db, user_id=123)
        self.assertTrue(user.onboarding_completed)

    async def test_rpc_auth_and_input(self):
        for token, user_id, code in [("bad", "123", grpc.StatusCode.UNAUTHENTICATED), ("work-test-token", "0", grpc.StatusCode.INVALID_ARGUMENT), ("work-test-token", "9223372036854775808", grpc.StatusCode.INVALID_ARGUMENT)]:
            with patch.object(rpc, "get_settings", return_value=SETTINGS), self.assertRaises(RpcError) as caught:
                await rpc.AuthServiceServicer().CompleteOnboarding(pb.CompleteOnboardingRequest(user_id=user_id), Context(token))
            self.assertEqual(caught.exception.code, code)

    async def test_rpc_success_and_missing_user(self):
        db = AsyncMock()
        session = AsyncMock()
        session.__aenter__.return_value = db
        for user in [SimpleNamespace(is_active=1, onboarding_completed=False), None]:
            with patch.object(rpc, "get_settings", return_value=SETTINGS), patch.object(rpc, "AsyncSessionLocal", return_value=session), patch.object(auth.auth_repository, "get_user_by_id", new=AsyncMock(return_value=user)):
                if user is None:
                    with self.assertRaises(RpcError) as caught:
                        await rpc.AuthServiceServicer().CompleteOnboarding(pb.CompleteOnboardingRequest(user_id="123"), Context())
                    self.assertEqual(caught.exception.code, grpc.StatusCode.NOT_FOUND)
                else:
                    response = await rpc.AuthServiceServicer().CompleteOnboarding(pb.CompleteOnboardingRequest(user_id="123", transaction_id="trace"), Context())
                    self.assertTrue(response.onboarding_completed)
                    self.assertEqual(response.transaction_id, "trace")

    def test_openapi_requires_bearer_for_me(self):
        self.assertEqual(app.openapi()["paths"]["/api/auth/me"]["get"]["security"], [{"HTTPBearer": []}])


if __name__ == "__main__":
    unittest.main()
