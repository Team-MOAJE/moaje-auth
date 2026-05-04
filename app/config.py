"""Application configuration (pydantic-settings)

이 서비스는 Auth DB(단일 DB) 기반으로 동작하는 구성을 목표로 합니다.
현재 파일은 설정 항목 정의를 위한 문서형 스텁입니다.

## 필수 환경변수(초안)
- DATABASE_URL: MySQL 접속 문자열
- SECRET_KEY: JWT 서명용 비밀키(운영에서는 반드시 길고 랜덤)
- ALGORITHM: 예) HS256
- ACCESS_TOKEN_EXPIRE_MINUTES

## 옵션(추후)
- REFRESH_TOKEN_EXPIRE_DAYS
- PASSWORD_HASH_SCHEME (bcrypt 등)
- KEY_ROTATION_VERSION (mfa/account_token 암복호화 키 버전)
"""

# TODO(구현 시):
# - class Settings(BaseSettings): ...
# - env 파일 로딩(.env) / 운영 환경변수

