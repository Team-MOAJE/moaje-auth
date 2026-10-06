"""인증 HTTP 라우터 정의."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import (
    REQUIRED_ACTION_RE_LOGIN,
    REQUIRED_ACTION_RETRY_LATER,
    error_response,
    success_response,
)
from app.db.session import get_db
from app.core.security import TokenValidationError, validate_access_token as validate_jwt
from app.repositories.auth import get_user_by_id
from app.schemas.auth import CurrentUserResponse
from app.schemas.auth import (
    CreateAccountTokenRequest,
    CreateAccountTokenResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PinResetRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    SessionUnlockRequest,
    SmsRequest,
    SmsRequestResponse,
    SmsVerifyRequest,
    SmsVerifyResponse,
    TokenResponse,
    ValidateAccountTokenRequest,
    ValidateAccountTokenResponse,
    ValidateAccessTokenRequest,
    ValidateAccessTokenResponse,
)
from app.schemas.common import ApiResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_auth = HTTPBearer(auto_error=False)


@router.post("/sms/request", response_model=ApiResponse[SmsRequestResponse])
async def request_sms(
    request: Request,
    payload: SmsRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        result = await auth_service.request_sms_verification(
            db,
            phone_number=payload.phone_number,
            purpose=payload.purpose,
        )
    except auth_service.DuplicateUserError as exc:
        return error_response(
            request,
            status_code=409,
            code="AUTH-409-002",
            message="이미 가입된 번호입니다. 로그인해 주세요.",
            reason=str(exc),
        )
    except auth_service.UserNotFoundError as exc:
        return error_response(
            request,
            status_code=404,
            code="AUTH-404-002",
            message="가입된 사용자를 찾을 수 없습니다.",
            reason=str(exc),
        )
    except auth_service.SmsDeliveryUnavailableError as exc:
        return error_response(
            request,
            status_code=503,
            code="AUTH-503-001",
            message="SMS 발송 서비스를 사용할 수 없습니다.",
            reason=str(exc),
            required_action=REQUIRED_ACTION_RETRY_LATER,
        )
    except (ValueError, auth_service.SmsVerificationError) as exc:
        return error_response(
            request,
            status_code=400,
            code="AUTH-400-005",
            message="전화번호를 확인해 주세요.",
            reason=str(exc),
        )
    data = SmsRequestResponse(
        verification_id=result.verification_id,
        expires_in=result.expires_in,
        dev_code=result.dev_code,
    )
    return success_response(
        request,
        status_code=200,
        code="AUTH-200-008",
        message="인증번호를 발송했습니다.",
        data=data.model_dump(),
    )


@router.post("/sms/verify", response_model=ApiResponse[SmsVerifyResponse])
async def verify_sms(
    request: Request,
    payload: SmsVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        result = await auth_service.verify_sms_code(
            db,
            verification_id=payload.verification_id,
            code=payload.code,
        )
    except auth_service.SmsVerificationError as exc:
        return error_response(
            request,
            status_code=401,
            code="AUTH-401-006",
            message="SMS 인증에 실패했습니다.",
            reason=str(exc),
        )
    data = SmsVerifyResponse(
        verification_token=result.verification_token,
        expires_in=result.expires_in,
    )
    return success_response(
        request,
        status_code=200,
        code="AUTH-200-009",
        message="SMS 인증이 완료되었습니다.",
        data=data.model_dump(),
    )


@router.get("/me", response_model=ApiResponse[CurrentUserResponse])
async def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_auth),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        payload = validate_jwt(credentials.credentials)
        user_id = auth_service.parse_user_id(payload["sub"])
    except (TokenValidationError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid access token") from None
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is unavailable")
    return success_response(
        request,
        status_code=200,
        code="AUTH-200-007",
        message="사용자 정보 조회가 완료되었습니다.",
        data=CurrentUserResponse(
            user_id=str(user.user_id),
            onboarding_completed=user.onboarding_completed,
        ).model_dump(),
    )


@router.post(
    "/register",
    response_model=ApiResponse[RegisterResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        result = await auth_service.register_phone_user(
            db,
            verification_token=payload.verification_token,
            name=payload.name,
            pin=payload.pin,
            terms_version=payload.terms_version,
            privacy_version=payload.privacy_version,
            email=payload.email,
            device_info=payload.device_info,
        )
    except auth_service.DuplicateUserError as exc:
        return error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            code="AUTH-409-001",
            message="이미 가입된 사용자입니다.",
            reason=str(exc),
        )
    except auth_service.SmsVerificationError as exc:
        return error_response(
            request,
            status_code=401,
            code="AUTH-401-006",
            message="SMS 인증이 필요합니다.",
            reason=str(exc),
        )

    data = RegisterResponse(
        user_id=str(result.user_id),
        phone_number=result.phone_number,
        name=result.name,
        onboarding_completed=result.onboarding_completed,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=result.tokens.expires_in,
    )
    return success_response(
        request,
        status_code=status.HTTP_201_CREATED,
        code="AUTH-201-001",
        message="회원가입이 완료되었습니다.",
        data=data.model_dump(),
    )


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        tokens, onboarding_completed = await auth_service.login_phone_user(
            db,
            verification_token=payload.verification_token,
            pin=payload.pin,
            device_info=payload.device_info,
        )
    except auth_service.SmsVerificationError as exc:
        return error_response(
            request,
            status_code=401,
            code="AUTH-401-006",
            message="SMS 인증이 필요합니다.",
            reason=str(exc),
        )
    except auth_service.PinLockedError as exc:
        return error_response(
            request,
            status_code=423,
            code="AUTH-423-001",
            message="간편 비밀번호 인증이 잠겼습니다.",
            reason=str(exc),
        )
    except auth_service.InvalidCredentialsError as exc:
        return error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="AUTH-422-001",
            message="인증정보가 일치하지 않습니다.",
            reason=str(exc),
        )

    data = TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        onboarding_completed=onboarding_completed,
    )
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


@router.post("/session/unlock", response_model=ApiResponse[TokenResponse])
async def session_unlock(
    request: Request,
    payload: SessionUnlockRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        tokens, onboarding_completed = await auth_service.unlock_session(
            db,
            refresh_token=payload.refresh_token,
            pin=payload.pin,
        )
    except auth_service.PinLockedError as exc:
        return error_response(
            request,
            status_code=423,
            code="AUTH-423-001",
            message="간편 비밀번호 인증이 잠겼습니다.",
            reason=str(exc),
        )
    except (
        auth_service.InvalidCredentialsError,
        auth_service.InvalidRefreshTokenError,
    ) as exc:
        return error_response(
            request,
            status_code=401,
            code="AUTH-401-005",
            message="다시 로그인해 주세요.",
            reason=str(exc),
            required_action=REQUIRED_ACTION_RE_LOGIN,
        )
    data = TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        onboarding_completed=onboarding_completed,
    )
    return success_response(
        request,
        status_code=200,
        code="AUTH-200-010",
        message="앱 잠금이 해제되었습니다.",
        data=data.model_dump(),
    )


@router.post("/pin/reset", response_model=ApiResponse[MessageResponse])
async def pin_reset(
    request: Request,
    payload: PinResetRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        await auth_service.reset_pin(
            db,
            verification_token=payload.verification_token,
            new_pin=payload.new_pin,
        )
    except auth_service.SmsVerificationError as exc:
        return error_response(
            request,
            status_code=401,
            code="AUTH-401-006",
            message="SMS 인증이 필요합니다.",
            reason=str(exc),
        )
    except auth_service.UserNotFoundError as exc:
        return error_response(
            request,
            status_code=404,
            code="AUTH-404-002",
            message="가입된 사용자를 찾을 수 없습니다.",
            reason=str(exc),
        )
    return success_response(
        request,
        status_code=200,
        code="AUTH-200-011",
        message="간편 비밀번호가 변경되었습니다. 다시 로그인해 주세요.",
        data=MessageResponse(message="ok").model_dump(),
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
