# User API 설계
 
## 공통 기준
 
```
API prefix:                 /api/v1
JWT algorithm:               HS256
Access Token 만료:           30분
Refresh Token 만료:          7일
Refresh Cookie 이름:         refresh_token
Refresh Cookie 옵션:         HttpOnly=True, Secure=False(local), SameSite=lax, Path=/
비밀번호 해싱:                Argon2 (pwdlib)
인증 실패:                    401 Unauthorized
권한 부족:                    403 Forbidden
회원가입 성공:                201 Created
로그인·조회·갱신 성공:         200 OK
로그아웃·비밀번호 변경:        204 No Content
기본 role:                    PENDING
```
 
---
 
## 담당 파트
 
| 담당 | 공식 담당 범위 | 핵심 파일·기능 | 담당자 |
| --- | --- | --- | --- |
| 1 | Argon2와 인증 스키마 | `security.py`, 인증 schema, 비밀번호 해시·검증 |
| 2 | 회원가입·로그인 | signup/login API, service, 사용자 조회·토큰 발급 연결 |
| 3 | JWT 인증 dependency | Access Token 검증, `get_current_user`, `/users/me` |
| 4 | Refresh·로그아웃 | Refresh Cookie 검증·갱신·삭제 |
| 5 | 관리자 인가 | role 검사, 관리자 사용자 목록·역할 변경 |
 
공식 merge 순서: **담당 1 → 담당 2 → 담당 3 → 담당 4 → 담당 5**
 
## 구현 순서
 
앞 단계의 결과가 다음 단계의 입력이 되므로, 아래 순서를 지켜서 구현한다.
 
| 단계 | 내용 | 완료 조건 |
| --- | --- | --- |
| 1단계 | Argon2 해시/검증 함수 확인 (`hash_password`, `verify_password`) | 평문 비밀번호 미저장, 응답 schema에 `hashed_password` 미포함 |
| 2단계 | 회원가입·로그인 구현 | 잘못된 로그인은 401, Access Token은 body, Refresh Token은 Cookie |
| 3단계 | JWT 검증 dependency (`get_current_user`) 구현 후 `/users/me`에 적용 | 토큰 없음/무효/만료 시 401, 정상 토큰으로 `/users/me` 호출 성공 |
| 4단계 | Refresh 갱신 + 로그아웃 구현 | 유효한 Refresh Token으로 재발급, Access Token으로 refresh 시도는 거부, 로그아웃 후 Cookie 삭제 |
| 5단계 | 역할 기반 인가(`require_roles`) 구현 | 미인증 401, 인증했지만 권한 없음 403, 관리자 API는 ADMIN만 실행 |
 
## 요구사항 → 구현 위치 변환표
 
| 요구사항 표현 | 구현 위치 | 확인 내용 |
| --- | --- | --- |
| 가입할 수 있다 | API + service | 입력 검증, 중복 이메일, Argon2 해시 |
| 가입된 이메일과 비밀번호로 로그인 | API + service | 사용자 조회, `verify_password`, 토큰 발급 |
| 로그인된 사용자는 | dependency | Access Token 검증, 현재 사용자 조회 |
| 의료인 역할을 가진 유저만 | authorization dependency | `role` 또는 `department` 검사 |
| 로그아웃할 수 있다 | API + token 정책 | Refresh Cookie 삭제, 필요하면 서버 측 폐기 정책 |
| Access Token과 Refresh Token 발급 | login/refresh API | JSON body와 HTTP-only Cookie 위치 확인 |
 
API 함수에는 요구사항 ID를 주석으로 남겨 리뷰 시 누락을 방지한다.
 
```python
# [REQ-USER-002] 가입된 이메일과 비밀번호로 로그인을 할 수 있다.
@router.post("/users/login")
async def login(...):
    ...
```
 
---
 
## 1. 회원가입
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원가입 API |
| 설명 | 이메일, 비밀번호 등을 입력하여 신규 계정을 생성한다 |
| 엔드포인트(Endpoint) | `/api/v1/users/signup` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N |
 
### 2. 요청(Request)
 
**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 타입 |
 
**본문 예시**
```json
{
  "email": "example@example.com",
  "password": "Password123!",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678"
}
```
 
**본문 필드**
| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 사용자 이메일 (중복 불가) |
| password | string | Y | 비밀번호. 대문자·소문자·숫자·특수문자 각 1개 이상, 8자 이상 |
| name | string | Y | 이름 |
| department | string | Y | `MEDICAL`, `DEV`, `RESEARCH` 중 하나 |
| gender | string | Y | `M`, `F` 중 하나 |
| phone_number | string | Y | 휴대폰 번호 (중복 불가) |
 
### 3. 응답(Response)
 
**성공**
- 201 Created
```json
{
  "id": 1,
  "email": "example@example.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "PENDING",
  "is_active": true,
  "created_at": "2026-07-16T10:00:00"
}
```
응답에 `hashed_password`는 절대 포함하지 않는다.
 
**실패**
- 400 Bad Request
```json
{ "detail": "weak_password" }
```
| 필드명 | 설명 |
| --- | --- |
| weak_password | 대소문자·숫자·특수문자 각 1개 이상, 8자 이상 조건을 만족하지 못한 경우 |
| invalid_email_format | 이메일 형식이 올바르지 않은 경우 |
| empty_fields | 필수 필드 중 비어있는 값이 있는 경우 |
- 409 Conflict
```json
{ "detail": "email_already_exists" }
```
 
### 4. 비고
- 비밀번호는 Argon2(pwdlib)로 해시하여 `hashed_password` 컬럼에 저장한다. 평문 저장 금지.
- 가입 직후 `role`은 무조건 `PENDING`이다.
---
 
## 2. 로그인
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 로그인 API |
| 설명 | 이메일, 비밀번호를 통해 로그인하고 JWT를 발급받는다 |
| 엔드포인트(Endpoint) | `/api/v1/users/login` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N |
 
### 2. 요청(Request)
 
**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/x-www-form-urlencoded | `OAuth2PasswordRequestForm` 사용 |
 
**본문 예시** (JSON이 아니라 form 형식)
```
username=example@example.com&password=Password123!
```
 
**본문 필드**
| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| username | string | Y | 이메일을 넣는다 (`OAuth2PasswordRequestForm` 고정 필드명) |
| password | string | Y | 비밀번호 |
 
### 3. 응답(Response)
 
**성공**
- 200 OK
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```
추가로 `Set-Cookie` 헤더로 `refresh_token`을 `HttpOnly` 쿠키로 전달한다 (body에 포함하지 않음).
 
**실패**
- 401 Unauthorized
```json
{ "detail": "invalid_email_or_password" }
```
| 필드명 | 설명 |
| --- | --- |
| invalid_email_or_password | 이메일 혹은 비밀번호가 잘못된 경우 (계정 존재 여부는 노출하지 않음) |
| inactive_account | 비활성화된 계정으로 로그인 시도한 경우 |
 
### 4. 비고
- 프론트엔드와의 계약에 따라 `OAuth2PasswordRequestForm`을 사용하므로 JSON이 아닌 form-urlencoded로 받는다.
- Access Token payload: `sub`, `type="access"`, `iat`, `exp`.
- 로그인 실패는 400이 아니라 401로 응답한다 (팀 기준).
---
 
## 3. 토큰 재발급
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 액세스 토큰 재발급 API |
| 설명 | 만료된 액세스 토큰을 리프레시 토큰으로 재발급받는다 |
| 엔드포인트(Endpoint) | `/api/v1/users/refresh` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N (단, 유효한 refresh_token 쿠키 필요) |
 
### 2. 요청(Request)
 
**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Cookie | refresh_token=`<refresh_token>` | 로그인 시 발급된 쿠키가 자동 첨부됨 |
 
본문 없음.
 
### 3. 응답(Response)
 
**성공**
- 200 OK
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```
 
**실패**
- 401 Unauthorized
```json
{ "detail": "refresh_token_expired" }
```
| 필드명 | 설명 |
| --- | --- |
| refresh_token_expired | 리프레시 토큰도 만료된 경우, 재로그인 필요 |
| refresh_token_missing | 쿠키에 리프레시 토큰이 없는 경우 |
| refresh_token_invalid | 위변조되었거나, Access Token을 잘못 제출한 경우 (`type != "refresh"`) |
 
### 4. 비고
- 프론트엔드는 401을 받으면 자동으로 재로그인 페이지로 유도하므로, 실패 응답은 반드시 401이어야 한다 (400 금지).
---
 
## 4. 로그아웃
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 로그아웃 API |
| 설명 | 현재 세션을 종료하고 리프레시 토큰 쿠키를 만료시킨다 |
| 엔드포인트(Endpoint) | `/api/v1/users/logout` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | Y |
 
### 2. 요청(Request)
 
**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |
 
본문 없음.
 
### 3. 응답(Response)
 
**성공**
- 204 No Content
`Set-Cookie`로 `refresh_token`을 발급 시와 동일한 조건(`HttpOnly`, `Secure=False`, `SameSite=lax`, `Path=/`)으로 즉시 만료시킨다.
 
**실패**
- 401 Unauthorized
```json
{ "detail": "unauthorized" }
```
 
### 4. 비고
- 로그아웃은 Access Token 만료로 서버 세션을 없애는 게 아니라 Refresh Cookie를 지우는 방식이라, 이미 탈취된 Refresh Token까지 무효화하진 못한다는 한계가 있다.
---
 
## 5. 마이페이지 조회
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 내 정보 조회 API |
| 설명 | 로그인한 유저 본인의 정보를 조회한다 |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |
 
### 2. 요청(Request)
 
**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |
 
### 3. 응답(Response)
 
**성공**
- 200 OK
```json
{
  "id": 1,
  "email": "example@example.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "STAFF"
}
```
 
**실패**
- 401 Unauthorized
```json
{ "detail": "unauthorized" }
```
 
---
 
## 6. 회원 정보 수정
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 내 정보 수정 API |
| 설명 | 로그인한 유저 본인의 부서, 휴대폰 번호를 부분 수정한다 |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |
 
### 2. 요청(Request)
 
**본문 예시**
```json
{
  "phone_number": "01099998888"
}
```
 
**본문 필드**
| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| department | string | N | `MEDICAL`, `DEV`, `RESEARCH` 중 하나 |
| phone_number | string | N | 휴대폰 번호 (중복 불가) |
 
### 3. 응답(Response)
 
**성공**
- 200 OK
```json
{
  "id": 1,
  "department": "MEDICAL",
  "phone_number": "01099998888"
}
```
 
**실패**
- 409 Conflict
```json
{ "detail": "phone_number_already_exists" }
```
 
---
 
## 7. 비밀번호 변경
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 비밀번호 변경 API |
| 엔드포인트(Endpoint) | `/api/v1/users/me/password` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |
 
### 2. 요청(Request)
 
**본문 예시**
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```
 
**본문 필드**
| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| current_password | string | Y | 기존 비밀번호 (Argon2 `verify_password`로 검증) |
| new_password | string | Y | 새 비밀번호. 대소문자·숫자·특수문자 각 1개 이상, 8자 이상 |
 
### 3. 응답(Response)
 
**성공**
- 204 No Content
**실패**
- 400 Bad Request
```json
{ "detail": "current_password_mismatch" }
```
| 필드명 | 설명 |
| --- | --- |
| current_password_mismatch | 기존 비밀번호가 일치하지 않는 경우 |
| weak_password | 새 비밀번호가 정책을 만족하지 못하는 경우 |
 
---
 
## 8. 회원 탈퇴
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 탈퇴 API |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `DELETE` |
| 인증 필요 여부 | Y |
 
### 2. 요청(Request)
 
**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |
 
본문 없음 (팀 기준: password 확인 절차 없이 즉시 삭제).
 
### 3. 응답(Response)
 
**성공**
- 204 No Content
**실패**
- 401 Unauthorized
```json
{ "detail": "unauthorized" }
```
 
### 4. 비고
- 탈퇴 시 DB에서 즉시 하드 삭제(hard delete)한다.
---
 
## 9. 관리자 - 회원 목록 조회
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 관리자 회원 목록 조회 API |
| 엔드포인트(Endpoint) | `/api/v1/admin/users` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y (ADMIN 권한 필요) |
 
### 2. 요청(Request)
 
**쿼리 파라미터**
| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| keyword | string | N | 이메일 또는 이름으로 검색 |
| department | string | N | 부서 필터 |
 
### 3. 응답(Response)
 
**성공**
- 200 OK
```json
{
  "items": [
    {
      "id": 1,
      "email": "example@example.com",
      "name": "홍길동",
      "department": "MEDICAL",
      "gender": "M",
      "phone_number": "01012345678",
      "is_active": true
    }
  ]
}
```
 
**실패**
- 403 Forbidden
```json
{ "detail": "admin_permission_required" }
```
 
---
 
## 10. 관리자 - 회원 권한 변경
 
### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 관리자 회원 권한 변경 API |
| 엔드포인트(Endpoint) | `/api/v1/admin/users/role` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y (ADMIN 권한 필요) |
 
### 2. 요청(Request)
 
**본문 예시** (user_id를 path가 아닌 body에 포함 — 팀 기준)
```json
{
  "user_id": 5,
  "role": "STAFF"
}
```
 
**본문 필드**
| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| user_id | integer | Y | 권한을 변경할 대상 회원 ID |
| role | string | Y | `PENDING`, `STAFF`, `ADMIN` 중 하나 |
 
### 3. 응답(Response)
 
**성공**
- 200 OK
```json
{
  "id": 5,
  "role": "STAFF"
}
```
 
**실패**
- 403 Forbidden
```json
{ "detail": "admin_permission_required" }
```
- 404 Not Found
```json
{ "detail": "user_not_found" }
```
- 400 Bad Request
```json
{ "detail": "cannot_change_own_role" }
```
 
### 4. 비고
- 관리자 본인 권한 변경 방지: `user_id`가 현재 로그인한 관리자 본인의 ID와 같으면 `400 cannot_change_own_role`로 거부한다. (관리자가 실수로 자기 자신을 강등시켜 시스템에서 잠기는 사고 방지)
