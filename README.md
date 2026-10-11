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
- 내부 서비스용 gRPC 인터페이스 제공
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
| Internal API | REST / gRPC |
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
- `CompleteOnboarding`

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
REFRESH_TOKEN_EXPIRE_DAYS=7

PIN_MAX_ATTEMPTS=5
PIN_LOCK_MINUTES=30

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
| GET | `/api/auth/me` | Bearer JWT로 본인 ID, 온보딩 완료 상태 조회 |
| PATCH | `/api/auth/me` | 이름, 이메일 수정 |
| DELETE | `/api/auth/me` | 현재 PIN 확인 후 회원 탈퇴, 개인정보 제거 및 세션 폐기 |
| GET | `/.well-known/jwks.json` | Gateway JWT 검증용 RSA 공개키 조회 |
| POST | `/api/auth/register` | 전화번호, 이름, 선택 이메일, 6자리 PIN으로 회원가입 및 세션 발급 |
| POST | `/api/auth/login` | 전화번호, PIN으로 로그인 및 세션 발급 |
| POST | `/api/auth/session/unlock` | 유효한 세션과 PIN으로 앱 잠금 해제 및 토큰 교체 |
| POST | `/api/auth/pin/change` | Bearer JWT와 현재 PIN 확인 후 PIN 변경 및 기존 세션 전체 폐기 |
| POST | `/api/auth/refresh` | refresh token rotation |
| POST | `/api/auth/logout` | refresh token 폐기 |
| POST | `/api/auth/token/validate` | body 기반 access token 검증 |
| GET | `/api/auth/token/validate` | Authorization Bearer 기반 access token 검증 |
| POST | `/api/auth/account-token` | account token 생성 |
| POST | `/api/auth/account-token/validate` | account token 검증 |
| GET | `/health` | 헬스체크 |
| GET | `/ready` | MySQL 연결을 포함한 요청 처리 준비 상태 확인 |

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

### 전화번호 기반 계정 흐름

전화번호는 E.164 형식으로 정규화하고 형식, 중복만 검사함. 소유 인증값으로 취급하지 않으며 로그인 식별자로 사용함. JWT `sub`에는 내부 `user_id`를 사용함.

회원가입은 전화번호, 이름, 선택 이메일, 6자리 PIN, 약관 동의를 받음. 성별과 별도 아이디는 받지 않음.

PIN은 숫자 6자리이며 bcrypt 해시만 저장함. 실패 잠금과 PIN 변경은 서버에서 처리하고 변경 시 모든 Refresh Token을 폐기함. SMS를 사용하지 않아 PIN 분실 재설정은 제공하지 않음.

## 7. 토큰 정책

### Access Token

- 클라이언트는 다음 형식으로 Access Token을 전달함.

`Authorization: Bearer {access_token}`

- 기본 만료 시간은 30분이며 `ACCESS_TOKEN_EXPIRE_MINUTES`로 설정함.
- 로그아웃 또는 회원 탈퇴 시 Refresh Token은 즉시 폐기함.
- 이미 발급된 Access Token은 별도 blacklist를 사용하지 않아 만료 시점까지 서명 검증을 통과할 수 있음.
- 즉시 차단이 필요하면 Redis blacklist를 추가하며, 현재 범위에서는 짧은 만료 시간과 Refresh Token 폐기를 사용함.

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

RS256 JWT에 `kid`를 포함하고 Gateway는 JWKS 공개키로 검증함. 개인키는 Auth에만 보관함. 키는 PEM 원문 또는 마운트된 파일 경로로 설정함.

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

## 12. gRPC 및 온보딩 연동

gRPC 서버는 기본 `50051` 포트에서 실행한다. 계약은 별도 `moaje-grpc-contracts` 레포에서 관리한다.

### 제공 RPC

- `ValidateAccessToken`: Access Token 검증
- `CheckMfaRequired`: MFA 활성 여부 조회
- `ValidateAccountToken`: Account Token 검증
- `CompleteOnboarding`: Work가 완료한 재무 온보딩 상태 반영

### 온보딩 상태

- 신규 회원은 `onboarding_completed=false`로 생성한다.
- 앱은 `GET /api/auth/me`로 현재 상태를 조회한다.
- Work는 온보딩 답변을 저장한 뒤 `CompleteOnboarding`을 호출한다.
- 완료 요청을 여러 번 호출해도 성공하도록 처리한다.
- 사용자 ID는 JWT의 `sub`를 사용하며 온보딩 상태는 JWT에 넣지 않는다.

### 서비스 인증 및 TLS

- Work 호출은 `WORK_SERVICE_TOKEN`으로 인증한다.
- `GRPC_TLS_CERT`와 `GRPC_TLS_KEY`가 있으면 TLS로 실행한다.
- 인증서가 없으면 로컬 개발용 insecure 모드로 실행한다.

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
- 전화번호 형식, 중복 검사 및 6자리 PIN 기반 회원가입/로그인
- 서버 기반 PIN 실패 잠금, 로그인 상태 PIN 변경 및 세션 전체 폐기
- 이름, 이메일 수정 및 PIN 확인 기반 회원 탈퇴
- JWT Access Token 발급 및 검증
- Refresh Token 해시 저장
- Refresh Token Rotation
- REST 기반 token validate API
- AES-256-GCM 암복호화 유틸
- Account Token 매핑 로직
- 온보딩 완료 상태 조회 및 Work 연동
- RS256 JWT, `kid`, JWKS 공개키 제공
- gRPC AuthService (ValidateAccessToken, CheckMfaRequired, ValidateAccountToken, CompleteOnboarding)
- Dockerfile 작성

추후 확장:

- OAuth Kakao/Google
- TOTP MFA
- WebAuthn/FIDO2
- Kafka 이벤트 발행
- Redis blacklist
- AWS Secrets Manager 연동
