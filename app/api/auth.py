"""인증 HTTP 라우터 정의."""

from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _not_implemented(feature: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{feature} is not implemented yet.",
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest) -> RegisterResponse:
    _not_implemented("PIN registration")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    _not_implemented("PIN login")


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest) -> TokenResponse:
    _not_implemented("Refresh token rotation")


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest) -> MessageResponse:
    _not_implemented("Logout")
