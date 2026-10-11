"""Pydantic 요청 및 응답 스키마."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RegisterRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    pin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    pin_confirm: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    terms_agreed: Literal[True]
    privacy_agreed: Literal[True]
    terms_version: str = Field(..., min_length=1, max_length=50)
    privacy_version: str = Field(..., min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    device_info: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def pins_match(self) -> "RegisterRequest":
        if self.pin != self.pin_confirm:
            raise ValueError("간편 비밀번호가 일치하지 않습니다.")
        return self


class CurrentUserResponse(BaseModel):
    user_id: str
    onboarding_completed: bool


class RegisterResponse(BaseModel):
    user_id: str
    phone_number: str
    name: str
    onboarding_completed: bool
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)
    pin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    device_info: str | None = Field(default=None, max_length=500)


class SessionUnlockRequest(BaseModel):
    refresh_token: str = Field(..., min_length=32)
    pin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class PinChangeRequest(BaseModel):
    current_pin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_pin: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_pin_confirm: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")

    @model_validator(mode="after")
    def pins_match(self) -> "PinChangeRequest":
        if self.new_pin != self.new_pin_confirm:
            raise ValueError("간편 비밀번호가 일치하지 않습니다.")
        return self


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    onboarding_completed: bool | None = None


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
