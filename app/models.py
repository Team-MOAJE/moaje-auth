"""SQLAlchemy ORM models (ERD-first)

이 파일은 DB 스키마(ERD)를 코드로 옮길 때 기준점이 되는 문서 겸 스텁입니다.

## DB 전제
- DB: MySQL (InnoDB 권장)
- PK: `BIGINT` Snowflake

## ERD 테이블(핵심)
- `users`
	- `user_id` (BIGINT, Snowflake)
	- `email` (UNIQUE)
	- `is_active` (TINYINT)
	- `created_at`, `updated_at`

- `oauth_accounts`
	- `oauth_id` (BIGINT, AUTO_INCREMENT)
	- `user_id` (FK -> users.user_id)
	- `provider` (VARCHAR(20))
	- `provider_uid` (VARCHAR(255))
	- Unique: (`provider`, `provider_uid`)

- `refresh_tokens`
	- `token_id` (BIGINT, AUTO_INCREMENT)
	- `user_id` (FK)
	- `token_hash` (VARCHAR(512), UNIQUE)  # refresh token 원문 저장 금지
	- `device_info` (VARCHAR(500), NULL)
	- `issued_at`, `expires_at`
	- `is_revoked` (TINYINT)

- `webauthn_credentials`
	- `credential_id` (VARCHAR(512), PK)
	- `user_id` (FK)
	- `public_key_enc` (TEXT)  # 저장 시 암호화 여부/키 버전은 정책에 따름
	- `aaguid` (VARCHAR(36), NULL)
	- `sign_count` (BIGINT)
	- `device_name` (VARCHAR(255), NULL)
	- `created_at`, `last_used_at`

- `mfa_configs`
	- `mfa_id` (BIGINT, AUTO_INCREMENT)
	- `user_id` (FK)
	- `totp_secret_enc` (VARCHAR(512))  # AES-256-GCM 등으로 암호화 저장
	- `key_version` (INT)               # 키 로테이션 식별자
	- `is_enabled` (TINYINT)
	- `created_at`, `last_verified_at`

- `account_token_mappings`
	- `mapping_id` (BIGINT, AUTO_INCREMENT)
	- `user_id` (FK)
	- `account_token` (VARCHAR(255), UNIQUE)     # 외부/자산/계좌 식별 토큰(정책 합의 필요)
	- `encrypted_account_no` (VARCHAR(512))      # 민감정보: 암호화 저장
	- `key_version` (INT)
	- `is_active` (TINYINT)
	- `created_at`

## 구현 메모 ... 
- MySQL에서 FK/Index/Unique 제약은 Alembic 마이그레이션으로 관리하는 것을 권장
- Snowflake `user_id` 생성기(앱 레이어)는 별도 모듈로 분리하는 편이 유지보수에 좋을 듯 ... 
"""

# TODO(구현 시):
# - SQLAlchemy Base import 및 모델 클래스 정의
# - 관계(Relationship) 정의 (users 중심 1:N)
# - MySQL 타입/인덱스/제약조건 반영

