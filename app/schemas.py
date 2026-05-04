"""Pydantic schemas (request/response)

ERD 기반 API 계약을 정리...

## 기본(Auth)
- RegisterRequest / RegisterResponse
- LoginRequest / TokenResponse(access/refresh)
- RefreshRequest
- LogoutRequest

## OAuth(소셜)
- OAuthLoginRequest(provider, code/redirect_uri 등)
- OAuthLinkRequest

## MFA(TOTP)
- TotpEnrollResponse(qr/provisioning_uri)
- TotpVerifyRequest(code)

## WebAuthn (이 부분은 프론트와 ... )
- WebAuthnRegisterOptions / WebAuthnRegisterVerify
- WebAuthnAuthOptions / WebAuthnAuthVerify
"""

