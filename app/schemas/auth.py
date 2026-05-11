"""Pydantic 요청 및 응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    pin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class RegisterResponse(BaseModel):
    user_id: int
    email: str
    is_active: bool


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    pin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=32)
    all_devices: bool = False


class MessageResponse(BaseModel):
    message: str
