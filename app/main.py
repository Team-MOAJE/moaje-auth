"""FastAPI 애플리케이션 진입점"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.auth import router as auth_router


app = FastAPI(title="moaje-auth")
app.include_router(auth_router)

# 헬스체크 ... 간단하게 status만 구현함.
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
