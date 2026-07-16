# 4일차 - User API 설계

> `4일차 - User 사용자 요구사항 정의서` 를 기반으로 작성한 API 명세서.
> 엔드포인트와 규약은 **팀 공통 기준 문서(`4일차_인증인가_JWT_Argon2_튜토리얼`)** 를 따름.
> 프론트엔드 템플릿(`static/apis.js`)의 호출 규약과 일치.

---

## 0. 공통 규약

> 아래 값은 팀 공통 기준으로 **고정**한다. 담당자가 임의로 변경하지 않는다.

### 고정 기준

```
JWT algorithm:             HS256
JWT secret 환경변수:        JWT_SECRET_KEY
Access Token 만료:          30분
Refresh Token 만료:         7일
Access Token payload:      sub, type="access", iat, exp
Refresh Token payload:     sub, type="refresh", iat, exp
Refresh Cookie 이름:        refresh_token
Refresh Cookie:            HttpOnly=True, Secure=False(local), SameSite=lax, Path=/
인증 실패:                  401 Unauthorized
권한 부족:                  403 Forbidden
회원가입 성공:              201 Created
로그인·조회·갱신 성공:       200 OK
로그아웃·비밀번호 변경:      204 No Content
기본 role:                 PENDING
```

### 사용 라이브러리

| 용도 | 라이브러리 |
|---|---|
| 비밀번호 해싱 | **`pwdlib[argon2]`** |
| JWT | **`pyjwt`** |
| 인증 스킴 | **`HTTPBearer`** (fastapi.security) |
| 로그인 폼 | `OAuth2PasswordRequestForm` |

### Base URL

```
/api/v1
```

### 공통 Headers

| Key | Value | 설명 |
|---|---|---|
| Content-Type | `application/json` | 기본 요청 타입 (로그인 제외) |
| Authorization | `Bearer <access_token>` | 인증 필요 API |

### 공통 에러 응답 형식

```json
{ "detail": "에러 메시지" }
```

Pydantic 검증 실패(422)는 FastAPI가 자동 생성하며 `detail` 이 배열 형태다.

```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "올바른 이메일 형식이 아닙니다.", "type": "value_error" }
  ]
}
```

### 공통 상태 코드

| 코드 | 의미 |
|---|---|
| 200 | 조회/수정 성공 |
| 201 | 생성 성공 |
| 204 | 삭제 성공 (본문 없음) |
| 400 | 잘못된 요청 |
| 401 | 인증 실패 (토큰 없음/만료/불일치) |
| 403 | 권한 없음 (인증은 됐으나 역할 부족) |
| 404 | 리소스 없음 |
| 409 | 중복 (이메일, 휴대폰 번호) |
| 422 | 입력값 검증 실패 |

### 검증 규칙

| 항목 | 규칙 |
|---|---|
| email | 이메일 형식, 최대 255자, 중복 불가 |
| password | **대문자·소문자·숫자·특수문자 각 1개 이상, 8자 이상** |
| name | 2~20자 |
| phone_number | 최대 20자, 중복 불가 |
| gender | `M` / `F` |
| department | `MEDICAL` / `DEV` / `RESEARCH` |
| role | `PENDING` / `STAFF` / `ADMIN` |

### 권한 체계

| role | 설명 |
|---|---|
| `PENDING` | 대기자 — 마이페이지 외 모든 서비스 접근 불가 |
| `STAFF` | 스태프 — 흉부 X-ray 관련 모든 읽기/쓰기/수정 가능 |
| `ADMIN` | 어드민 — 모든 데이터 접근 가능 |

### API 목록

| # | 요구사항 ID | API | 메서드 | 엔드포인트 | 인증 | 담당 |
|---|---|---|---|---|---|---|
| 1 | REQ-USER-001 | 회원가입 | POST | `/users/signup` | N | 2 |
| 2 | REQ-USER-002 | 로그인 | POST | `/users/login` | N | 2 |
| 3 | NFR-USER-001 | 토큰 재발급 | POST | `/users/refresh` | 쿠키 | 4 |
| 4 | REQ-USER-003 | 로그아웃 | POST | `/users/logout` | Y | 4 |
| 5 | REQ-USER-006 | 마이페이지 조회 | GET | `/users/me` | Y | **3** |
| 6 | REQ-USER-007 | 회원 정보 수정 | PATCH | `/users/me` | Y | 3 |
| 7 | REQ-USER-008 | 비밀번호 변경 | PATCH | `/users/me/password` | Y | 3 |
| 8 | REQ-USER-009 | 회원 탈퇴 | DELETE | `/users/me` | Y | 3 |
| 9 | REQ-USER-004 | 회원 목록 조회 | GET | `/admin/users` | Y + ADMIN | 5 |
| 10 | REQ-USER-005 | 회원 권한 변경 | PATCH | `/admin/users/role` | Y + ADMIN | 5 |

### 담당 파트 및 구현 순서

앞 단계의 결과가 다음 단계의 입력이 되므로 **순서대로 구현·머지**한다.

| 담당 | 범위 | 핵심 파일 |
|---|---|---|
| 1 | Argon2와 인증 스키마 | `core/security.py`(해시), `schemas/auth.py` |
| 2 | 회원가입·로그인 | signup/login API, service, 토큰 발급 |
| **3** | **JWT 인증 dependency** | **`get_current_user`, `/users/me`** |
| 4 | Refresh·로그아웃 | Refresh Cookie 검증·갱신·삭제 |
| 5 | 관리자 인가 | `require_roles`, admin API |

```
담당 1 → 담당 2 → 담당 3 → 담당 4 → 담당 5
```

---

## 1. 회원가입 API

### 1-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원가입 API |
| 요구사항 ID | REQ-USER-001 |
| 설명 | 사내 구성원이 이메일, 비밀번호, 이름, 부서, 성별, 휴대폰 번호를 입력하여 회원가입 |
| 엔드포인트 | `/api/v1/users/signup` |
| 메서드 | `POST` |
| 인증 필요 여부 | N |

### 1-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Content-Type | application/json | 요청 타입 |

**본문 예시**

```json
{
  "email": "doctor@hospital.com",
  "password": "Password123!",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| email | string | Y | 사용자 이메일 (중복 불가, 최대 255자) |
| password | string | Y | 비밀번호 (대소문자·숫자·특수문자 각 1개 이상, 8자 이상) |
| name | string | Y | 사용자 이름 (2~20자) |
| department | string(enum) | Y | `MEDICAL` / `DEV` / `RESEARCH` |
| gender | string(enum) | Y | `M` / `F` |
| phone_number | string | Y | 휴대폰 번호 (중복 불가) |

### 1-3. 응답(Response)

**성공 — 201 Created**

```json
{
  "id": 1,
  "email": "doctor@hospital.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "PENDING",
  "is_active": true
}
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| id | integer | 사용자 고유 ID |
| email | string | 이메일 |
| name | string | 이름 |
| department | string | 부서 |
| gender | string | 성별 |
| phone_number | string | 휴대폰 번호 |
| role | string | 권한 (가입 시 `PENDING` 고정) |
| is_active | boolean | 계정 활성화 여부 |

**실패 — 409 Conflict**

```json
{ "detail": "이미 사용 중인 이메일입니다." }
```

| detail | 조건 |
|---|---|
| 이미 사용 중인 이메일입니다. | email 중복 |
| 이미 사용 중인 휴대폰 번호입니다. | phone_number 중복 |

**실패 — 422 Unprocessable Entity**

Pydantic 검증 실패 (이메일 형식, 비밀번호 규칙, 이름 길이, Enum 값 등)

### 1-4. 비고

- 비밀번호는 **평문 저장 금지**. `argon2` 로 해싱하여 `hashed_password` 컬럼에 저장한다.
- 응답에 `hashed_password` 는 **절대 포함하지 않는다** (`response_model` 로 차단).
- 가입 직후 권한은 `PENDING` 이며, 관리자가 권한을 부여해야 서비스 이용이 가능하다.
- 이메일/휴대폰 중복 검사는 Pydantic 스키마가 아닌 **서비스 계층**에서 수행한다 (DB 조회가 필요하므로).

---

## 2. 로그인 API

### 2-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 사용자 로그인 API |
| 요구사항 ID | REQ-USER-002, NFR-USER-001 |
| 설명 | 이메일, 비밀번호를 활용한 로그인 및 JWT 발급 |
| 엔드포인트 | `/api/v1/users/login` |
| 메서드 | `POST` |
| 인증 필요 여부 | N |

### 2-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Content-Type | application/x-www-form-urlencoded | **OAuth2 표준 폼 형식** |

**본문 필드** (`OAuth2PasswordRequestForm`)

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| username | string | Y | **이메일** (OAuth2 규격상 필드명이 `username`) |
| password | string | Y | 비밀번호 |

**요청 예시**

```
POST /api/v1/users/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=Password123!
```

### 2-3. 응답(Response)

**성공 — 200 OK**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Set-Cookie 헤더**

```
Set-Cookie: refresh_token=<token>; HttpOnly; Path=/; Max-Age=604800; SameSite=Lax
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| access_token | string | JWT 액세스 토큰 (만료 30분) |
| token_type | string | `bearer` 고정 |

**실패 — 401 Unauthorized**

```json
{ "detail": "이메일 또는 비밀번호가 일치하지 않습니다." }
```

| detail | 조건 |
|---|---|
| 이메일 또는 비밀번호가 일치하지 않습니다. | 이메일 없음 **또는** 비밀번호 불일치 |
| 비활성화된 계정입니다. | `is_active = false` |

### 2-4. 비고

- **로그인 실패 시 "이메일이 없음"과 "비밀번호 틀림"을 구분하지 않는다.** 구분하면 공격자가 가입된 이메일 목록을 알아낼 수 있다 (계정 열거 공격).
- `Content-Type` 이 JSON이 아니라 **form-data** 인 이유: FastAPI의 `OAuth2PasswordRequestForm` 표준을 사용하면 Swagger UI의 Authorize 버튼과 연동된다. 프론트(`apis.js`)도 `FormData` 로 전송한다.
- **Access Token**: 30분, JSON 응답으로 전달 → 클라이언트가 보관
- **Refresh Token**: 7일, **http_only 쿠키**로 전달 → JavaScript가 접근 불가 (XSS 방어)
- **JWT payload 고정**: `sub`(user_id 문자열), `type`("access"/"refresh"), `iat`, `exp`. 민감 정보는 넣지 않는다 (payload는 누구나 디코딩 가능).
- `sub` 는 문자열로 저장하므로 검증 시 `int(payload["sub"])` 로 변환한다.

---

## 3. 토큰 재발급 API

### 3-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 액세스 토큰 재발급 API |
| 요구사항 ID | NFR-USER-001 |
| 설명 | Refresh Token으로 만료된 Access Token을 재발급 |
| 엔드포인트 | `/api/v1/users/refresh` |
| 메서드 | `POST` |
| 인증 필요 여부 | 쿠키 (refresh_token) |

### 3-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Cookie | `refresh_token=<token>` | 브라우저가 자동 전송 |

본문 없음.

### 3-3. 응답(Response)

**성공 — 200 OK**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**실패 — 401 Unauthorized**

```json
{ "detail": "유효하지 않은 리프레시 토큰입니다." }
```

| detail | 조건 |
|---|---|
| 리프레시 토큰이 없습니다. | 쿠키 없음 |
| 유효하지 않은 리프레시 토큰입니다. | 토큰 위조/만료 |

### 3-4. 비고

- 프론트(`apis.js`)는 **401 응답을 받으면 자동으로 이 API를 호출**하고, 성공 시 원래 요청을 재시도한다.
- 재발급도 실패하면 프론트가 자동 로그아웃 처리한다 → 재로그인 유도.
- Refresh Token은 요청 본문이 아닌 **쿠키에서 읽는다** (`Cookie` 파라미터 사용).

---

## 4. 로그아웃 API

### 4-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 로그아웃 API |
| 요구사항 ID | REQ-USER-003 |
| 설명 | Refresh Token 쿠키 삭제 |
| 엔드포인트 | `/api/v1/users/logout` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y |

### 4-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 필수 |

본문 없음.

### 4-3. 응답(Response)

**성공 — 204 No Content**

본문 없음.

**Set-Cookie 헤더** (쿠키 삭제)

```
Set-Cookie: refresh_token=; HttpOnly; Path=/; Max-Age=0; SameSite=lax
```

**실패 — 401 Unauthorized**

```json
{ "detail": "인증이 필요합니다." }
```

### 4-4. 비고

- JWT는 **stateless** 이므로 서버가 Access Token을 강제 만료시킬 수 없다. 로그아웃은 Refresh Token 쿠키를 삭제하여 재발급을 막는 방식이다.
- Access Token은 남은 만료 시간(최대 30분) 동안 유효하다. 즉시 무효화가 필요하면 Refresh Token의 `jti` 를 DB/Redis에 저장해 폐기 여부를 검사해야 하나, 이번 과제 범위 밖.
- **쿠키 삭제 시 발급할 때와 동일한 `key`, `path`, `domain` 조건**을 사용해야 브라우저가 기존 쿠키를 삭제한다.
- 프론트는 로그아웃 후 로그인 페이지로 전환한다.

---

## 5. 마이페이지 조회 API

### 5-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 내 정보 조회 API |
| 요구사항 ID | REQ-USER-006 |
| 설명 | 로그인한 사용자 본인의 정보 조회 |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y |

### 5-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 필수 |

본문 없음.

### 5-3. 응답(Response)

**성공 — 200 OK**

```json
{
  "id": 1,
  "email": "doctor@hospital.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "STAFF"
}
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| id | integer | 고유 ID |
| email | string | 이메일 |
| name | string | 이름 |
| department | string | 부서 |
| gender | string | 성별 |
| phone_number | string | 휴대폰 번호 |
| role | string | 권한 |

**실패 — 401 Unauthorized**

```json
{ "detail": "인증이 필요합니다." }
```

### 5-4. 비고

- **경로 등록 순서 주의**: `/users/me` 를 `/users/{user_id}` 보다 **먼저** 등록해야 한다. 순서가 반대면 `"me"` 를 `user_id(int)` 로 변환하려다 422가 발생한다.
- `PENDING` 권한도 마이페이지는 접근 가능하다 (요구사항: "대기자는 마이페이지 외 모든 서비스 접근 불가").

---

## 6. 회원 정보 수정 API

### 6-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 내 정보 수정 API |
| 요구사항 ID | REQ-USER-007 |
| 설명 | 본인의 부서, 휴대폰 번호를 부분 수정 (Partial Update) |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |

### 6-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Content-Type | application/json | 요청 타입 |
| Authorization | `Bearer <access_token>` | 필수 |

**본문 예시**

```json
{
  "department": "RESEARCH",
  "phone_number": "01098765432"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| department | string(enum) | N | `MEDICAL` / `DEV` / `RESEARCH` |
| phone_number | string | N | 휴대폰 번호 (중복 불가) |

### 6-3. 응답(Response)

**성공 — 200 OK**

마이페이지 조회와 동일한 형식 (수정된 정보 반환)

**실패 — 400 Bad Request**

```json
{ "detail": "수정할 항목이 없습니다." }
```

**실패 — 409 Conflict**

```json
{ "detail": "이미 사용 중인 휴대폰 번호입니다." }
```

### 6-4. 비고

- **Partial Update**: 모든 필드가 선택 항목이며, 전달된 필드만 수정한다.
- 구현 시 `payload.model_dump(exclude_unset=True)` 를 사용한다. 이걸 빼면 **전달하지 않은 필드가 `None` 으로 덮어써져** 데이터가 소실된다.
- 모든 필드가 비어있으면 `400` 을 반환한다.
- 수정 대상은 **부서, 휴대폰 번호뿐**이다. 이메일, 이름, 성별은 수정 불가.

---

## 7. 비밀번호 변경 API

### 7-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 비밀번호 변경 API |
| 요구사항 ID | REQ-USER-008 |
| 설명 | 기존 비밀번호 검증 후 새 비밀번호로 변경 |
| 엔드포인트 | `/api/v1/users/me/password` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |

### 7-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Content-Type | application/json | 요청 타입 |
| Authorization | `Bearer <access_token>` | 필수 |

**본문 예시**

```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| current_password | string | Y | 기존 비밀번호 |
| new_password | string | Y | 새 비밀번호 (대소문자·숫자·특수문자 각 1개 이상, 8자 이상) |

### 7-3. 응답(Response)

**성공 — 204 No Content**

본문 없음.

**실패 — 400 Bad Request**

| detail | 조건 |
|---|---|
| 기존 비밀번호가 일치하지 않습니다. | current_password 불일치 |
| 새 비밀번호가 기존 비밀번호와 동일합니다. | current == new |

**실패 — 422 Unprocessable Entity**

새 비밀번호가 검증 규칙 위반

### 7-4. 비고

- 기존 비밀번호 검증은 평문 비교가 아니라 **해시 검증**(`argon2.verify`)으로 수행한다.
- 새 비밀번호도 해싱하여 저장한다.
- 응답에 비밀번호 관련 정보를 절대 포함하지 않는다.

---

## 8. 회원 탈퇴 API

### 8-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원 탈퇴 API |
| 요구사항 ID | REQ-USER-009 |
| 설명 | 본인 계정 및 관련 정보 즉시 삭제 |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `DELETE` |
| 인증 필요 여부 | Y |

### 8-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 필수 |

본문 없음.

### 8-3. 응답(Response)

**성공 — 204 No Content**

본문 없음.

**실패 — 401 Unauthorized**

```json
{ "detail": "인증이 필요합니다." }
```

### 8-4. 비고

- 요구사항: "회원탈퇴 시 Database에서 회원과 관련된 정보는 **모두 즉시 삭제**한다" → **Hard Delete** (Soft Delete 아님).
- **FK 영향**: `xray_images.uploader_id` 는 `ON DELETE SET NULL` 이므로, 탈퇴해도 X-ray 이미지 자체는 남고 업로더 정보만 `NULL` 이 된다. 의료 데이터 보존을 위한 설계.
- 탈퇴 후 Refresh Token 쿠키도 삭제한다.

---

## 9. 회원 목록 조회 API (관리자)

### 9-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 전체 회원 목록 조회 API |
| 요구사항 ID | REQ-USER-004 |
| 설명 | 관리자가 전체 회원을 검색/필터하여 조회 |
| 엔드포인트 | `/api/v1/admin/users` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y (ADMIN 전용) |

### 9-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Authorization | `Bearer <access_token>` | ADMIN 권한 필요 |

**쿼리 파라미터**

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| search | string | N | 이메일 **또는** 이름으로 부분 검색 |
| department | string(enum) | N | 부서 필터 (`MEDICAL` / `DEV` / `RESEARCH`) |

**요청 예시**

```
GET /api/v1/admin/users?search=홍길동&department=MEDICAL
```

### 9-3. 응답(Response)

**성공 — 200 OK**

```json
[
  {
    "id": 1,
    "email": "doctor@hospital.com",
    "name": "홍길동",
    "department": "MEDICAL",
    "gender": "M",
    "phone_number": "01012345678",
    "role": "STAFF",
    "is_active": true
  }
]
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| id | integer | 고유 ID |
| email | string | 이메일 |
| name | string | 이름 |
| department | string | 부서 |
| gender | string | 성별 |
| phone_number | string | 휴대폰 번호 |
| role | string | 권한 |
| is_active | boolean | 계정 활성화 여부 |

**실패 — 403 Forbidden**

```json
{ "detail": "관리자 권한이 필요합니다." }
```

### 9-4. 비고

- **401과 403의 구분**: 토큰이 없거나 만료면 `401`, 토큰은 유효하나 ADMIN이 아니면 `403`.
- `search` 는 이메일과 이름 **양쪽**을 대상으로 하는 OR 검색이다.
- 검색과 필터는 **동시 적용 가능**하다 (AND 조건).
- 권한 검사는 `Depends(require_admin)` 의존성으로 처리한다.

---

## 10. 회원 권한 변경 API (관리자)

### 10-1. API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | 회원 권한 변경 API |
| 요구사항 ID | REQ-USER-005 |
| 설명 | 관리자가 특정 회원의 권한을 변경 |
| 엔드포인트 | `/api/v1/admin/users/role` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y (ADMIN 전용) |

### 10-2. 요청(Request)

**Headers**

| Key | Value | 설명 |
|---|---|---|
| Content-Type | application/json | 요청 타입 |
| Authorization | `Bearer <access_token>` | ADMIN 권한 필요 |

**본문 예시**

```json
{
  "user_id": 3,
  "role": "STAFF"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| user_id | integer | Y | 권한을 변경할 대상 회원 ID |
| role | string(enum) | Y | `PENDING` / `STAFF` / `ADMIN` |

### 10-3. 응답(Response)

**성공 — 200 OK**

```json
{
  "id": 3,
  "email": "staff@hospital.com",
  "name": "김민수",
  "role": "STAFF"
}
```

**실패 — 403 Forbidden**

```json
{ "detail": "관리자 권한이 필요합니다." }
```

**실패 — 404 Not Found**

```json
{ "detail": "존재하지 않는 사용자입니다." }
```

### 10-4. 비고

- 대상 `user_id` 를 **경로가 아닌 본문**으로 받는다. 프론트(`apis.js`)의 `adminUpdateUserRole(roleData)` 규약을 따른 것.
- **본인의 권한 변경 방지** 로직 검토 필요 (관리자가 자신을 STAFF로 낮추면 시스템에 ADMIN이 사라질 수 있음) → 팀 논의 필요.

---

## 11. 구현 시 공통 사항

### 계층 구조 (팀 공통 기준)

```
app/
  core/
    config.py       # DB/JWT 설정
    security.py     # Argon2 해시, JWT 생성/검증 공통 함수
  schemas/
    auth.py         # 회원가입, 로그인, 토큰 응답 스키마
  repositories/
    user.py         # 이메일/id로 사용자 조회
  services/
    auth.py         # 회원가입/로그인/토큰 갱신 업무 흐름
  apis/
    auth.py         # HTTP method, path, status code, dependency 연결
```

**다른 사람이 만든 함수의 이름과 반환 타입을 임의로 바꾸지 않는다.**

### 스키마 분리

| 스키마 | 용도 |
|---|---|
| `UserSignUpRequest` | 회원가입 입력 |
| `UserUpdateRequest` | 정보 수정 입력 (전 필드 Optional) |
| `PasswordChangeRequest` | 비밀번호 변경 입력 |
| `RoleUpdateRequest` | 권한 변경 입력 |
| `UserResponse` | 응답 (**hashed_password 제외**) |
| `TokenResponse` | 토큰 응답 (`access_token`, `token_type`) |

SQLAlchemy 객체를 그대로 반환하려면 `model_config = {"from_attributes": True}` 가 필요하다.

### 비밀번호 해싱 (담당 1)

```python
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
```

**해시 결과를 직접 비교하지 않고 반드시 `verify()` 를 사용한다.** Argon2는 salt가 해시 문자열에 포함되므로 같은 비밀번호도 매번 다른 해시가 나온다.

### JWT 생성 (담당 1~2)

```python
from datetime import datetime, timedelta, timezone
import jwt

def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

### 인증 의존성 (담당 3)

```python
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(async_get_db),
) -> User:
    """JWT 검증 → user_id 추출 → DB 조회 → User 반환"""
```

**`type != "access"` 검사 필수** — Refresh Token으로 일반 API를 호출하는 것을 막는다.

### 인가 의존성 (담당 5)

```python
def require_roles(*allowed_roles: Role):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
        return current_user
    return checker
```

`get_current_user` 는 **인증만** 담당하고, 역할 검사는 별도 의존성이 담당한다.

### 비동기 주의사항

- DB를 사용하는 모든 핸들러는 `async def` + `await` 필수
- 세션은 `db: AsyncSession = Depends(async_get_db)` 로 주입

### 추가 필요 패키지

```bash
uv add "pwdlib[argon2]" pyjwt
uv sync
```

`pyproject.toml` 과 `uv.lock` 을 함께 커밋한다. 팀원은 `uv sync` 로 동일 환경을 구성한다.

### 환경변수 (`.env`)

```
JWT_SECRET_KEY=충분히_긴_랜덤_문자열
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

랜덤 키 생성: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

**`.env` 는 커밋하지 않는다.** `.env.example` 에는 키 이름과 예시만 적는다.

---

## 12. 요구사항 → 구현 위치 변환표

| 요구사항 표현 | 구현 위치 | 확인 내용 |
|---|---|---|
| 가입할 수 있다 | API + service | 입력 검증, 중복 이메일, Argon2 해시 |
| 이메일과 비밀번호로 로그인 | API + service | 사용자 조회, `verify_password`, 토큰 발급 |
| **로그인된 사용자는** | **dependency** | **Access Token 검증, 현재 사용자 조회** |
| 관리자 권한을 가진 유저만 | authorization dependency | `role` 검사 |
| 로그아웃할 수 있다 | API + token 정책 | Refresh Cookie 삭제 |

API 함수에 요구사항 ID를 주석으로 남긴다.

```python
# [REQ-USER-006] 모든 로그인 유저는 마이페이지에서 본인의 정보를 확인할 수 있다.
@router.get("/users/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

---

## 13. 미해결 / 논의 필요

1. **비밀번호 검증 규칙이 팀 기준 문서에 없다.** 프론트(`apis.js`)의 에러 메시지는 **"대소문자, 특수문자, 숫자를 각 1개씩 포함한 8자리 이상"** 이다. Stage 2 연습 규칙(숫자 미포함, 8~20자)과 다르므로 **프론트 기준으로 통일** 필요 → 담당 1이 스키마에 반영.
2. **관리자 본인 권한 변경 방지** 로직 포함 여부.
3. **회원가입 후 자동 로그인 여부** — 현재 설계는 가입만 하고 별도 로그인이 필요한 구조.
4. **`is_active` 검사 위치** — `get_current_user` 에서 검사할지, 로그인 시에만 검사할지. (현재 설계: 양쪽 모두)
