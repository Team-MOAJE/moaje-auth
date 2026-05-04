"""Repository layer (DB access)

서비스 레이어가 DB 세부사항에 덜 의존하도록, CRUD/쿼리를 모아두는 계층입니다.
현재는 ERD 기반의 책임 경계를 문서로만 정의합니다.

## 책임(예시)
- Users
	- create/get_by_email/get_by_id/update_active
- OAuth Accounts
	- link_account/unlink/find_by_provider_uid
- Refresh Tokens
	- save_token_hash/revoke_token/is_token_revoked
- MFA/TOTP
	- upsert_totp_secret/enable/disable/update_last_verified
- WebAuthn
	- register_credential/update_sign_count/update_last_used
- Account Token Mappings
	- upsert_mapping/deactivate/list_by_user

## 보안 메모
- refresh token은 원문 저장 금지(해시 저장)
- account_no, totp_secret 등은 암호화 저장 + key_version으로 복호화 키 선택
"""

# TODO(구현 시):
# - SQLAlchemy Session 주입
# - 트랜잭션 경계(서비스 vs repository) 합의

