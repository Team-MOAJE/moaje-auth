"""AuthService gRPC 서버 구현체.

app/services/auth.py에 이미 있는 REST용 비즈니스 로직을 그대로 재사용한다.
"""

from __future__ import annotations

import time

import grpc

from app.db.session import AsyncSessionLocal
from app.rpc.proto import auth_service_pb2, auth_service_pb2_grpc
from app.services import auth as auth_service


def _now_ms() -> int:
    return int(time.time() * 1000)


class AuthServiceServicer(auth_service_pb2_grpc.AuthServiceServicer):
    async def ValidateAccessToken(
        self,
        request: auth_service_pb2.ValidateAccessTokenRequest,
        context: grpc.aio.ServicerContext,
    ) -> auth_service_pb2.ValidateAccessTokenResponse:
        result = auth_service.validate_access_token(request.access_token)
        return auth_service_pb2.ValidateAccessTokenResponse(
            transaction_id=request.transaction_id,
            is_valid=result.is_valid,
            user_id=result.user_id,
            expires_at=result.expires_at,
            timestamp=_now_ms(),
        )

    async def ValidateAccountToken(
        self,
        request: auth_service_pb2.ValidateAccountTokenRequest,
        context: grpc.aio.ServicerContext,
    ) -> auth_service_pb2.ValidateAccountTokenResponse:
        async with AsyncSessionLocal() as db:
            result = await auth_service.validate_account_token(db, account_token=request.account_token)

        return auth_service_pb2.ValidateAccountTokenResponse(
            transaction_id=request.transaction_id,
            is_valid=result.is_valid,
            user_id=str(result.user_id) if result.user_id is not None else "",
            is_active=result.is_active,
            timestamp=_now_ms(),
        )

    async def CheckMfaRequired(
        self,
        request: auth_service_pb2.CheckMfaRequiredRequest,
        context: grpc.aio.ServicerContext,
    ) -> auth_service_pb2.CheckMfaRequiredResponse:
        try:
            user_id = int(request.user_id)
        except ValueError:
            return auth_service_pb2.CheckMfaRequiredResponse(
                transaction_id=request.transaction_id,
                is_mfa_required=False,
                timestamp=_now_ms(),
            )

        async with AsyncSessionLocal() as db:
            required = await auth_service.is_mfa_required(db, user_id=user_id)

        return auth_service_pb2.CheckMfaRequiredResponse(
            transaction_id=request.transaction_id,
            is_mfa_required=required,
            timestamp=_now_ms(),
        )
