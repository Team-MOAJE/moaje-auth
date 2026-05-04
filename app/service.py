"""Service layer (business logic)

API 라우터(app/api.py)에서 호출하는 비즈니스 규칙을 모아두는 계층

## 인증 수단(ERD 기준)
1) Password 기반 로그인
2) 소셜 로그인 연동(oauth_accounts)
3) Refresh Token 관리(refresh_tokens)
4) MFA(TOTP)(mfa_configs)
5) WebAuthn/FIDO2(webauthn_credentials)

## 핵심 규칙(결정 필요)
- Snowflake user_id 생성 주체
- Refresh Token 정책: 해시 저장 + 로테이션 여부
- MFA Secret / 계좌정보 암호화: AES-256-GCM + key_version 로테이션
- 계정/토큰 매핑(account_token_mappings)은 Auth 도메인 소유 여부/권한 경계 정의
"""

# TODO(구현 시):
# - password hash/verify
# - jwt issue/verify
# - refresh token rotation
# - totp enroll/verify

