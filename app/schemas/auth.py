"""Pydantic 요청 및 응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    pin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    device_info: str | None = Field(default=None, max_length=500)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ValidateAccessTokenRequest(BaseModel):
    access_token: str = Field(..., min_length=1)


class ValidateAccessTokenResponse(BaseModel):
    is_valid: bool
    user_id: str = ""
    expires_at: int = 0


class CreateAccountTokenRequest(BaseModel):
    user_id: int
    account_number: str = Field(..., min_length=1, max_length=255)
    transaction_id: str | None = Field(default=None, max_length=100)


class CreateAccountTokenResponse(BaseModel):
    account_token: str
    user_id: int


class ValidateAccountTokenRequest(BaseModel):
    account_token: str = Field(..., min_length=1, max_length=255)
    transaction_id: str | None = Field(default=None, max_length=100)


class ValidateAccountTokenResponse(BaseModel):
    is_valid: bool
    user_id: int | None = None
    is_active: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=32)
    all_devices: bool = False


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
