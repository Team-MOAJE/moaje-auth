"""Common REST response schemas."""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str | None = None
    reason: str


class ErrorBody(BaseModel):
    reason: str
    details: list[ErrorDetail]
    requiredAction: Literal[
        "NONE",
        "RE_LOGIN",
        "REFRESH_TOKEN",
        "MFA_AUTH",
        "RETRY",
        "RETRY_LATER",
        "CONTACT_SUPPORT",
    ]


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    status: int
    code: str
    message: str
    data: T | None
    error: ErrorBody | None
    traceId: str
    timestamp: str
