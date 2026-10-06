"""환경변수 기반 애플리케이션 설정."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="moaje-auth", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")

    database_url: str = Field(default="mysql+asyncmy://user:password@localhost:3306/moaje_auth?charset=utf8mb4", alias="DATABASE_URL")

    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    jwt_private_key: str | None = Field(default=None, alias="JWT_PRIVATE_KEY")
    jwt_public_key: str | None = Field(default=None, alias="JWT_PUBLIC_KEY")
    jwt_issuer: str = Field(default="moaje-auth", alias="JWT_ISSUER")
    jwt_audience: str | None = Field(default=None, alias="JWT_AUDIENCE")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    sms_provider: str = Field(default="disabled", alias="SMS_PROVIDER")
    sms_otp_expire_minutes: int = Field(default=5, alias="SMS_OTP_EXPIRE_MINUTES")
    sms_otp_max_attempts: int = Field(default=5, alias="SMS_OTP_MAX_ATTEMPTS")
    sms_request_cooldown_seconds: int = Field(default=60, alias="SMS_REQUEST_COOLDOWN_SECONDS")
    sms_hourly_request_limit: int = Field(default=5, alias="SMS_HOURLY_REQUEST_LIMIT")
    sms_dev_expose_code: bool = Field(default=False, alias="SMS_DEV_EXPOSE_CODE")
    pin_max_attempts: int = Field(default=5, alias="PIN_MAX_ATTEMPTS")
    pin_lock_minutes: int = Field(default=30, alias="PIN_LOCK_MINUTES")

    aes_master_key: str = Field(default="change-me", alias="AES_MASTER_KEY")
    key_version: int = Field(default=1, alias="KEY_VERSION")

    grpc_port: int = Field(default=50051, alias="GRPC_PORT")
    work_service_token: str | None = Field(default=None, alias="WORK_SERVICE_TOKEN")
    grpc_tls_cert: str | None = Field(default=None, alias="GRPC_TLS_CERT")
    grpc_tls_key: str | None = Field(default=None, alias="GRPC_TLS_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
