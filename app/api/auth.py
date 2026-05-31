"""인증 HTTP 라우터 정의."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import (
    REQUIRED_ACTION_RE_LOGIN,
    REQUIRED_ACTION_RETRY_LATER,
    error_response,
    success_response,
)
from app.db.session import get_db
from app.schemas.auth import (
    CreateAccountTokenRequest,
    CreateAccountTokenResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    ValidateAccountTokenRequest,
    ValidateAccountTokenResponse,
    ValidateAccessTokenRequest,
    ValidateAccessTokenResponse,
)
from app.schemas.common import ApiResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        tokens = await auth_service.login_with_pin(db, email=payload.email, pin=payload.pin, device_info=payload.device_info)
    except auth_service.InvalidCredentialsError as exc:
        return error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="AUTH-422-001",
            message="인증정보가 일치하지 않습니다.",
            reason=str(exc),
        )

    data = TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token, expires_in=tokens.expires_in)
    return success_response(
        request,
        status_code=status.HTTP_200_OK,
        code="AUTH-200-001",
        message="로그인이 완료되었습니다.",
        data=data.model_dump(),
    )


@router.post("/token/validate", response_model=ApiResponse[ValidateAccessTokenResponse])
async def validate_token(request: Request, payload: ValidateAccessTokenRequest) -> JSONResponse:
    result = auth_service.validate_access_token(payload.access_token)
    data = ValidateAccessTokenResponse(is_valid=result.is_valid, user_id=result.user_id, expires_at=result.expires_at)
    return success_response(
        request,
        status_code=status.HTTP_200_OK,
        code="AUTH-200-004",
        message="토큰 검증이 완료되었습니다.",
        data=data.model_dump(),
    )


@router.get("/token/validate", response_model=ApiResponse[ValidateAccessTokenResponse])
async def validate_bearer_token(
    request: Request,
    authorization: str = Header(default=""),
) -> JSONResponse:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        data = ValidateAccessTokenResponse(is_valid=False)
        return success_response(
            request,
            status_code=status.HTTP_200_OK,
            code="AUTH-200-004",
            message="토큰 검증이 완료되었습니다.",
            data=data.model_dump(),
        )

    result = auth_service.validate_access_token(token)
    data = ValidateAccessTokenResponse(is_valid=result.is_valid, user_id=result.user_id, expires_at=result.expires_at)
    return success_response(
        request,
        status_code=status.HTTP_200_OK,
        code="AUTH-200-004",
        message="토큰 검증이 완료되었습니다.",
        data=data.model_dump(),
    )


@router.post("/account-token", response_model=ApiResponse[CreateAccountTokenResponse])
async def create_account_token(
    request: Request,
    payload: CreateAccountTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        result = await auth_service.create_account_token(
            db,
            user_id=payload.user_id,
            account_number=payload.account_number,
        )
    except auth_service.UserNotFoundError as exc:
        return error_response(
            request,
            status_code=status.HTTP_404_NOT_FOUND,
            code="AUTH-404-001",
            message="사용자를 찾을 수 없습니다.",
            reason=str(exc),
        )
    except auth_service.AccountTokenError as exc:
        return error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="AUTH-500-001",
            message="인증 처리 중 오류가 발생했습니다.",
            reason=str(exc),
            required_action=REQUIRED_ACTION_RETRY_LATER,
        )

    data = CreateAccountTokenResponse(
        account_token=result.account_token,
        user_id=result.user_id,
    )
    return success_response(
        request,
        status_code=status.HTTP_200_OK,
        code="AUTH-200-005",
        message="계좌 토큰이 생성되었습니다.",
        data=data.model_dump(),
    )


@router.post("/account-token/validate", response_model=ApiResponse[ValidateAccountTokenResponse])
async def validate_account_token(
    request: Request,
    payload: ValidateAccountTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await auth_service.validate_account_token(
        db,
        account_token=payload.account_token,
    )
    data = ValidateAccountTokenResponse(
        is_valid=result.is_valid,
        user_id=result.user_id,
        is_active=result.is_active,
    )
    return success_response(
        request,
        status_code=status.HTTP_200_OK,
        code="AUTH-200-006",
        message="계좌 토큰 검증이 완료되었습니다.",
        data=data.model_dump(),
    )


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    request: Request,
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        tokens = await auth_service.rotate_refresh_token(db, refresh_token=payload.refresh_token)
    except auth_service.InvalidRefreshTokenError as exc:
        return error_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTH-401-005",
            message="다시 로그인해 주세요.",
            reason=str(exc),
            required_action=REQUIRED_ACTION_RE_LOGIN,
        )

    data = TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token, expires_in=tokens.expires_in)
    return success_response(
        request,
        status_code=status.HTTP_200_OK,
        code="AUTH-200-002",
        message="토큰이 재발급되었습니다.",
        data=data.model_dump(),
    )


@router.post("/logout", response_model=ApiResponse[MessageResponse])
async def logout(
    request: Request,
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        await auth_service.logout(db, refresh_token=payload.refresh_token, all_devices=payload.all_devices)
    except auth_service.InvalidRefreshTokenError as exc:
        return error_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTH-401-005",
            message="다시 로그인해 주세요.",
            reason=str(exc),
            required_action=REQUIRED_ACTION_RE_LOGIN,
        )

    data = MessageResponse(message="ok")
    return success_response(
        request,
        status_code=status.HTTP_200_OK,
        code="AUTH-200-003",
        message="로그아웃이 완료되었습니다.",
        data=data.model_dump(),
    )
