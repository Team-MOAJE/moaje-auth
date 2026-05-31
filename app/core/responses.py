"""Common REST response envelope helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

REQUIRED_ACTION_NONE = "NONE"
REQUIRED_ACTION_RE_LOGIN = "RE_LOGIN"
REQUIRED_ACTION_REFRESH_TOKEN = "REFRESH_TOKEN"
REQUIRED_ACTION_RETRY_LATER = "RETRY_LATER"


def get_trace_id(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if isinstance(trace_id, str) and trace_id:
        return trace_id
    return str(uuid4())


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def success_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    data: Any,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "status": status_code,
            "code": code,
            "message": message,
            "data": data,
            "error": None,
            "traceId": get_trace_id(request),
            "timestamp": utc_timestamp(),
        },
    )


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    reason: str,
    details: list[dict[str, str]] | None = None,
    required_action: str = REQUIRED_ACTION_NONE,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "status": status_code,
            "code": code,
            "message": message,
            "data": None,
            "error": {
                "reason": reason,
                "details": details or [],
                "requiredAction": required_action,
            },
            "traceId": get_trace_id(request),
            "timestamp": utc_timestamp(),
        },
    )
