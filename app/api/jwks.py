"""Gateway용 JSON Web Key Set 공개 API."""

from fastapi import APIRouter, HTTPException, status

from app.core.security import TokenConfigurationError, get_jwks


router = APIRouter(tags=["jwks"])


@router.get("/.well-known/jwks.json", include_in_schema=True)
def jwks() -> dict[str, list[dict[str, str]]]:
    try:
        return get_jwks()
    except TokenConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
