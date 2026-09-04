# moaje-auth 기술 가이드 및 컨벤션

`moaje-auth` 인증/인가 서비스의 현재 구현 상태, DB 설계, 토큰 정책, 보안 컨벤션을 정리합니다.

---

## 1. 서비스 개요

`moaje-auth`는 Moaje 프로젝트의 인증/인가를 담당하는 서비스입니다.

### 주요 역할

- 사용자 인증
- JWT Access Token / Refresh Token 발급
- Refresh Token Rotation
- OAuth 연동(Kakao, Google) 예정
- MFA(TOTP) 예정
- WebAuthn/FIDO2 인증 정보 관리 예정
- Account Token 관리
- 내부 서비스용 gRPC 인터페이스 제공 예정
- Auth 관련 Kafka 이벤트 발행 예정

---

## 2. 기술 스택

| 구분 | 기술 |
| --- | --- |
| Language | Python 3.12+ |
| Framework | FastAPI |
| DB | MySQL 8.x |
| ORM | SQLAlchemy |
| Migration | Alembic |
| PIN Hash | bcrypt |
| Token Hash | SHA-256 |
| JWT | RS256 권장 / 초기 구현은 HS256 가능 |
| MFA | TOTP 예정 |
| OAuth | Kakao, Google / OAuth 2.0 예정 |
| Encryption | AES-256-GCM |
| Key Management | AWS Secrets Manager |
| Internal API | REST token validate 구현 / gRPC 예정 |
| Event Stream | Kafka 예정 |
| Cache / Session | Redis 예정 |
| Transport Security | TLS 1.3, gRPC-TLS |
| Monitoring | Slack Webhook |
| Git Security | .gitignore, git-secrets |

---

## 3. 통신 정책

Moaje 프로젝트의 통신 방식은 다음과 같이 구분합니다.

| 구분 | 방식 | 예시 |
| --- | --- | --- |
| 외부 요청 | REST API | 로그인, 회원가입, 토큰 재발급 |
| 내부 서비스 간 요청/응답 | gRPC | 토큰 검증, MFA 필요 여부 확인 |
| 비동기 이벤트 전달 | Kafka | 로그인 성공 이벤트, 토큰 폐기 이벤트 |

### Auth 기준 예시

#### REST API

- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`

#### gRPC

- `ValidateAccessToken`
- `CheckMfaRequired`
- `ValidateAccountToken`

#### Kafka Events

- `UserRegisteredEvent`
- `UserLoggedInEvent`
- `RefreshTokenRevokedEvent`
- `MfaStatusChangedEvent`
- `AccountTokenCreatedEvent`

---

## 4. DB / ID 전제

- DB는 MySQL 8.x를 사용한다.
- Storage Engine은 InnoDB를 사용한다.
- Charset은 `utf8mb4`를 권장한다.
- `users.user_id`는 Snowflake 기반 BIGINT를 사용한다.
- ID는 DB Auto Increment가 아니라 애플리케이션에서 생성한다.

### Snowflake 합의 필요 항목

- epoch 기준 시각
- worker_id 정책
- datacenter_id 정책
- clock rollback 발생 시 처리 방식

---

## 5. 환경 변수

`.env.example`을 참고하여 `.env`를 구성합니다.

### 필수 환경 변수

```env
APP_NAME=moaje-auth
APP_ENV=local

DATABASE_URL=mysql+asyncmy://user:password@localhost:3306/moaje_auth?charset=utf8mb4

SECRET_KEY=
ALGORITHM=HS256
JWT_ISSUER=moaje-auth
# JWT_AUDIENCE=moaje-services
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=14

AES_MASTER_KEY=
KEY_VERSION=1

# 추후 사용 예정
# REDIS_HOST=localhost
# REDIS_PORT=6379
# KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

AES 키는 32바이트 URL-safe base64 값을 사용합니다.

```bash
python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

## 6. 현재 REST API

현재 구현된 REST API는 다음과 같습니다.

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/api/auth/register` | PIN 기반 회원가입 |
| POST | `/api/auth/login` | PIN 로그인 및 access/refresh token 발급 |
| POST | `/api/auth/refresh` | refresh token rotation |
| POST | `/api/auth/logout` | refresh token 폐기 |
| POST | `/api/auth/token/validate` | body 기반 access token 검증 |
| GET | `/api/auth/token/validate` | Authorization Bearer 기반 access token 검증 |
| POST | `/api/auth/account-token` | account token 생성 |
| POST | `/api/auth/account-token/validate` | account token 검증 |
| GET | `/health` | 헬스체크 |

### Docker 실행

앱과 MySQL을 함께 올릴 때는 Docker Compose를 사용합니다.

```bash
docker compose up --build
```

컨테이너가 뜬 뒤 DB 마이그레이션을 적용합니다.

```bash
docker compose exec app alembic upgrade head
```

헬스체크:

```bash
curl http://localhost:8000/health
```

Compose 환경에서는 MySQL이 호스트 `3307` 포트로 노출됩니다.

## 7. 토큰 정책

### Access Token

- 클라이언트는 다음 형식으로 Access Token을 전달한다.

`Authorization: Bearer {access_token}`

### JWT Claim (Principal Update)

JWT Claim은 최소화한다. 서명 검증 후 Banking/Asset이 요청자 식별에 사용하는 principal 정보는 아래 payload 그대로다.

| Claim | 타입 | 의미 | 비고 |
| --- | --- | --- | --- |
| sub | string | 사용자 ID (user_id) | 항상 포함 |
| typ | string | 토큰 타입("access") | 항상 포함. Refresh Token은 JWT가 아니라 별도 해시로 관리 |
| jti | string | 토큰 고유 ID | 항상 포함 |
| iat | number | 발급 시각 (Unix seconds) | 항상 포함 |
| exp | number | 만료 시각 (Unix seconds) | 항상 포함 |
| iss | string | 발급자("moaje-auth") | 항상 포함 |
| aud | string | 대상 서비스 | `JWT_AUDIENCE` 설정 시에만 포함 |
| transaction_id | string | 요청 추적용 ID | 호출 시 전달한 경우에만 포함 |

역할(role)/권한(permission) 관련 claim은 아직 없음 ... MFA/OAuth 등 확장 시 별도 검토 필요 !! 

gRPC `ValidateAccessToken`을 호출하면 위 payload를 직접 파싱할 필요 없이 `is_valid`, `user_id`, `expires_at`만 검증 결과로 받는다

---

## 8. Refresh Token 정책

Refresh Token은 원문을 저장하지 않는다.

- 원문 Refresh Token 저장 금지
- DB에는 SHA-256 해시값만 저장
- is_revoked 플래그로 폐기 여부 관리
- Refresh Token Rotation 적용 권장
- 새 Refresh Token 발급 시 기존 Refresh Token은 즉시 revoke 처리

저장 예시:
refresh_token 원문 → SHA-256 → token_hash 저장

---

## 9. 인증 컨벤션

### PIN

- PIN은 bcrypt로 해싱한다.
- 평문 PIN은 저장하지 않는다.
- 로그에 PIN을 출력하지 않는다.

### OAuth

- OAuth 계정은 (provider, provider_uid) 조합으로 unique 처리한다.
- 예시 provider:
  - kakao
  - google

### MFA / TOTP

- TOTP Secret은 평문 저장 금지
- totp_secret_enc에 AES-256-GCM으로 암호화하여 저장
- MFA 활성 여부는 mfa_configs.is_enabled를 기준으로 판단한다.

### WebAuthn / FIDO2

- credential_id를 기준으로 credential을 식별한다.
- sign_count 정책을 별도로 정의해야 한다.
- private key나 secret 계열 값은 저장하지 않는다.

---

## 10. Account Token 정책

계좌번호는 다른 서비스에 직접 노출하지 않는다.

- 실제 계좌번호는 Auth DB에 암호화하여 저장한다.
- 다른 서비스는 계좌번호 대신 account_token만 사용한다.
- account_token은 계좌번호를 대체하는 내부 식별 토큰이다.
- Asset, Banking 등 다른 도메인은 계좌번호 평문을 직접 다루지 않는다.

저장 대상:

- account_token → account_token_mappings.account_token
- account_no → account_token_mappings.encrypted_account_no (AES-256-GCM)

금지 사항:

- 계좌번호 평문 반환 금지
- encrypted_account_no를 API/gRPC/Kafka 응답에 포함 금지
- 계좌번호 로그 출력 금지

---

## 11. 암호화 / 키 관리

저장 암호화 대상:

- mfa_configs.totp_secret_enc
- account_token_mappings.encrypted_account_no

암호화 방식:

- AES-256-GCM 사용
- IV/Nonce 재사용 금지
- 인증 태그 함께 저장
- key_version으로 키 회전 가능하게 설계

키 관리:

- 운영 환경에서는 AWS Secrets Manager 사용
- 애플리케이션 코드에 키 하드코딩 금지
- DB에 마스터 키 저장 금지
- JWT 키와 AES 키 분리

---

## 12. gRPC 정책 (update)

서비스 간 동기 요청/응답 통신은 gRPC를 사용한다. proto 정의는 `moaje-grpc-contracts` 레포(`proto/grpc/auth_service.proto`)에서 관리하며, 이 레포에는 `third_party/moaje-grpc-contracts` git submodule로 참조한다.

Auth 서비스 주요 기능:

- Access Token 검증 (`ValidateAccessToken`)
- MFA 필요 여부 확인 (`CheckMfaRequired`)
- Account Token 유효성 검증 (`ValidateAccountToken`)

gRPC 서버는 FastAPI 앱과 같은 프로세스에서 `GRPC_PORT`(기본 50051)로 기동된다. proto가 변경되면 `scripts/gen_proto.sh`로 stub을 재생성한다.

### TLS (update)

`GRPC_TLS_CERT`/`GRPC_TLS_KEY`(PEM) 설정 시 TLS로 기동, 미설정 시 경고 로그와 함께 insecure로 폴백(로컬 전용으로, 운영환경에서는 안됨) 운영 환경에서는 필수

원칙:

- gRPC 응답에는 검증 결과만 포함
- 민감정보를 반환하지 않음
- transaction_id를 포함하여 로그 추적 가능하게 함
- timestamp는 Unix milliseconds 기준 사용

반환 금지 데이터:

- refresh_token 원문
- password hash
- TOTP secret
- encrypted account number
- 계좌번호 평문
- WebAuthn secret/private 정보

---

## 13. Kafka 이벤트 정책

Auth 도메인에서 발생한 사건은 추후 Kafka 이벤트로 발행한다.

예시:

- 회원가입 완료
- 로그인 성공
- Refresh Token 폐기
- MFA 상태 변경
- Account Token 생성

원칙:

- 이벤트는 이미 발생한 사실만 표현한다.
- 민감정보 포함 금지
- transaction_id, user_id, created_at 포함 권장

---

## 14. Redis 사용 계획

Redis 사용 용도:

- Access Token blacklist
- Refresh Token 상태 관리
- 로그인 시도 제한
- 임시 인증 코드 저장
- rate limit 보조

민감정보 원문 저장 금지

---

## 15. 로깅 / 모니터링 정책

로그 금지 대상:

- 비밀번호
- Access Token 원문
- Refresh Token 원문
- TOTP Secret
- 계좌번호
- 암호화 키
- OAuth 토큰

권장:

- 이메일 마스킹
- account_token만 기록
- transaction_id로 추적
- Slack webhook 알림 가능

---

## 16. Git 보안 컨벤션

- .env 커밋 금지
- secret key 커밋 금지
- DB 계정 정보 커밋 금지
- OAuth client secret 커밋 금지
- git-secrets 사용 권장

---

## 17. 초기 구현 범위

현재 구현:

- FastAPI health check
- Alembic 기반 Auth DB 스키마
- PIN 기반 회원가입/로그인
- JWT Access Token 발급 및 검증
- Refresh Token 해시 저장
- Refresh Token Rotation
- REST 기반 token validate API
- AES-256-GCM 암복호화 유틸
- Account Token 매핑 로직
- gRPC AuthService (ValidateAccessToken, CheckMfaRequired, ValidateAccountToken)
- Dockerfile 작성

추후 확장:

- OAuth Kakao/Google
- TOTP MFA
- WebAuthn/FIDO2
- Kafka 이벤트 발행
- Redis blacklist
- RS256 전환
- AWS Secrets Manager 연동
