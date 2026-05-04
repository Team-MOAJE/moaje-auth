"""FastAPI router definitions

현재는 ERD 기반으로 '어떤 엔드포인트가 필요할지'만 정리합니다.

## Auth(Password/JWT)
- POST /register
- POST /login
- POST /refresh
- POST /logout

## OAuth
- POST /oauth/{provider}/login
- POST /oauth/{provider}/link

## MFA(TOTP)
- POST /mfa/totp/enroll
- POST /mfa/totp/verify
- POST /mfa/totp/disable

## WebAuthn
- POST /webauthn/register/options
- POST /webauthn/register/verify
- POST /webauthn/auth/options
- POST /webauthn/auth/verify
"""

