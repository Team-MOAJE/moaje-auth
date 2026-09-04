"""FastAPI 애플리케이션 진입점"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth import router as auth_router
from app.core.responses import (
    REQUIRED_ACTION_NONE,
    REQUIRED_ACTION_RETRY_LATER,
    error_response,
    success_response,
)
from app.rpc.server import create_server
from app.schemas.auth import HealthResponse
from app.schemas.common import ApiResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    grpc_server = create_server()
    await grpc_server.start()
    try:
        yield
    finally:
        await grpc_server.stop(grace=5)


app = FastAPI(title="moaje-auth", lifespan=lifespan)
app.include_router(auth_router)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next: Any) -> JSONResponse:
    request.state.trace_id = request.headers.get("X-Trace-Id") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Trace-Id"] = request.state.trace_id
    return response


def _validation_error_code(path: str) -> tuple[str, str]:
    if path.endswith("/register"):
        return "AUTH-400-002", "회원가입 요청 검증에 실패했습니다."
    if path.endswith("/login"):
        return "AUTH-400-001", "로그인 요청 검증에 실패했습니다."
    return "AUTH-400-004", "요청값 검증에 실패했습니다."


def _validation_details(exc: RequestValidationError) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        loc = [str(part) for part in error.get("loc", []) if part != "body"]
        detail: dict[str, str] = {"reason": str(error.get("msg", "Invalid value"))}
        if loc:
            detail["field"] = ".".join(loc)
        details.append(detail)
    return details


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    code, reason = _validation_error_code(request.url.path)
    return error_response(
        request,
        status_code=status.HTTP_400_BAD_REQUEST,
        code=code,
        message="입력값을 다시 확인해 주세요.",
        reason=reason,
        details=_validation_details(exc),
        required_action=REQUIRED_ACTION_NONE,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    status_code = exc.status_code
    code = f"AUTH-{status_code}-001"
    message = "요청을 처리할 수 없습니다."
    required_action = REQUIRED_ACTION_NONE
    if status_code >= 500:
        code = "AUTH-500-001"
        message = "인증 처리 중 오류가 발생했습니다."
        required_action = REQUIRED_ACTION_RETRY_LATER

    return error_response(
        request,
        status_code=status_code,
        code=code,
        message=message,
        reason=str(exc.detail),
        required_action=required_action,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="AUTH-500-001",
        message="인증 처리 중 오류가 발생했습니다.",
        reason="Auth 내부 처리 중 예기치 않은 오류가 발생했습니다.",
        required_action=REQUIRED_ACTION_RETRY_LATER,
    )


@app.get("/health", response_model=ApiResponse[HealthResponse])
def health(request: Request) -> JSONResponse:
    return success_response(
        request,
        status_code=status.HTTP_200_OK,
        code="AUTH-200-000",
        message="Auth 서비스가 정상 동작 중입니다.",
        data={"status": "ok"},
    )
