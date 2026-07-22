# 4일차 USER API 설계

## 1. 문서 목적

이 문서는 4일차 사용자 요구사항과 현재 FastAPI 구현을 기준으로 사용자 인증·인가 API의 계약을 정의한다. 프론트엔드와 백엔드는 이 문서의 HTTP method, endpoint, 요청 형식, 응답 형식, 상태 코드를 공통 기준으로 사용한다.

### 공통 기준

| 항목 | 내용 |
| --- | --- |
| API prefix | `/api/v1` |
| 기본 응답 형식 | `application/json` |
| 로그인 요청 형식 | `application/x-www-form-urlencoded` |
| Access Token 전달 | `Authorization: Bearer <access_token>` |
| Refresh Token 전달 | `refresh_token` HTTP-only Cookie |
| 날짜 형식 | ISO 8601 문자열 |
| 비밀번호 저장 | Argon2 해시, 평문 저장 금지 |

### Enum 값

| 구분 | 허용 값 | 의미 |
| --- | --- | --- |
| `gender` | `male`, `female` | 성별 |
| `department` | `medical`, `dev`, `research` | 의료진, 개발팀, 연구진 |
| `role` | `pending`, `staff`, `admin` | 승인 대기, 내부 직원, 관리자 |

## 2. 요구사항과 endpoint

| 요구사항 ID | 기능 | Method | Endpoint | 인증·권한 |
| --- | --- | --- | --- | --- |
| REQ-USER-001 | 회원가입 | `POST` | `/api/v1/users/signup` | 불필요 |
| REQ-USER-002 | 로그인 | `POST` | `/api/v1/users/login` | 불필요 |
| NFR-USER-001 | Access Token 갱신 | `POST` | `/api/v1/users/refresh` | Refresh Cookie |
| REQ-USER-003 | 로그아웃 | `POST` | `/api/v1/users/logout` | 로그인 사용자 |
| REQ-USER-004 | 관리자 사용자 목록 | `GET` | `/api/v1/admin/users` | `admin` |
| REQ-USER-005 | 관리자 역할 변경 | `PATCH` | `/api/v1/admin/users/role` | `admin` |
| REQ-USER-006 | 내 정보 조회 | `GET` | `/api/v1/users/me` | 로그인 사용자 |
| REQ-USER-007 | 내 정보 수정 | `PATCH` | `/api/v1/users/me` | 로그인 사용자 |
| REQ-USER-008 | 비밀번호 변경 | `PATCH` | `/api/v1/users/me/password` | 로그인 사용자 |
| REQ-USER-009 | 회원 탈퇴 | `DELETE` | `/api/v1/users/me` | 로그인 사용자 |

## 3. 공통 응답

### 3.1 사용자 응답 객체

비밀번호와 `hashed_password`는 어떤 응답에도 포함하지 않는다.

```json
{
  "id": 5,
  "email": "user@example.com",
  "name": "홍길동",
  "phone_number": "01012345678",
  "gender": "male",
  "department": "medical",
  "role": "pending",
  "is_active": true
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | integer | 사용자 고유 ID |
| `email` | string | 사용자 이메일 |
| `name` | string | 사용자 이름 |
| `phone_number` | string | 휴대폰 번호 |
| `gender` | string | `male` 또는 `female` |
| `department` | string | `medical`, `dev`, `research` 중 하나 |
| `role` | string | `pending`, `staff`, `admin` 중 하나 |
| `is_active` | boolean | 계정 활성화 여부 |

### 3.2 오류 응답

```json
{
  "detail": "오류 내용"
}
```

Pydantic 입력 검증 실패 시 `detail`은 오류 객체 배열로 반환될 수 있다.

| 상태 코드 | 의미 |
| --- | --- |
| `200 OK` | 조회·수정·로그인·토큰 갱신 성공 |
| `201 Created` | 회원가입 성공 |
| `204 No Content` | 로그아웃·비밀번호 변경·회원 탈퇴 성공 |
| `400 Bad Request` | 중복 값, 비밀번호 규칙 위반, 수정 값 누락 |
| `401 Unauthorized` | 로그인 실패, 토큰 또는 Refresh Cookie 오류 |
| `403 Forbidden` | 로그인했지만 관리자 권한이 없음 |
| `404 Not Found` | 역할 변경 대상 사용자가 없음 |
| `422 Unprocessable Entity` | 필수 필드 누락 또는 요청 형식 오류 |

## 4. 회원가입

### `POST /api/v1/users/signup`

사내 구성원이 계정을 생성한다. 신규 계정의 기본 역할은 `pending`이다.

### Request

`Content-Type: application/json`

```json
{
  "email": "user@example.com",
  "password": "Password1!",
  "name": "홍길동",
  "phone_number": "01012345678",
  "gender": "male",
  "department": "medical"
}
```

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `email` | string | Y | 올바른 이메일 형식, 중복 불가 |
| `password` | string | Y | 8~20자, 대문자·소문자·숫자·특수문자 각 1개 이상 |
| `name` | string | Y | 사용자 이름 |
| `phone_number` | string | Y | 휴대폰 번호, 중복 불가 |
| `gender` | string | Y | `male`, `female` |
| `department` | string | Y | `medical`, `dev`, `research` |

### Response

- 성공: `201 Created`
- 본문: 공통 사용자 응답 객체
- 실패: 이메일·휴대폰 번호 중복 또는 비밀번호 규칙 위반 `400`, 입력 검증 실패 `422`

## 5. 로그인

### `POST /api/v1/users/login`

이메일과 비밀번호를 검증하고 Access Token과 Refresh Token을 발급한다.

### Request

`Content-Type: application/x-www-form-urlencoded`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `username` | string | Y | 사용자의 이메일을 입력 |
| `password` | string | Y | 평문 비밀번호, HTTPS로 전송 |
| `grant_type` | string | N | 사용하지 않으므로 생략 가능 |
| `scope` | string | N | 사용하지 않으므로 생략 가능 |
| `client_id` | string | N | 사용하지 않으므로 생략 가능 |
| `client_secret` | string | N | 사용하지 않으므로 생략 가능 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/users/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=user@example.com&password=Password1!'
```

### Response: `200 OK`

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer"
}
```

응답 헤더에는 다음 속성의 쿠키가 함께 설정된다.

```text
Set-Cookie: refresh_token=<token>; HttpOnly; SameSite=Lax; Path=/
```

이메일, 비밀번호 또는 활성화 상태가 올바르지 않으면 계정 존재 여부를 구분하지 않고 `401 Unauthorized`를 반환한다.

## 6. Access Token 갱신

### `POST /api/v1/users/refresh`

HTTP-only Cookie의 Refresh Token을 검증하고 새 Access Token을 발급한다. Request body는 없다.

### Response: `200 OK`

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer"
}
```

Refresh Cookie가 없거나, 만료·변조되었거나, refresh 타입 토큰이 아니거나, 사용자를 찾을 수 없으면 `401 Unauthorized`를 반환한다.

## 7. 로그아웃

### `POST /api/v1/users/logout`

인증된 사용자의 `refresh_token` 쿠키를 삭제한다.

### Headers

```text
Authorization: Bearer <access_token>
```

### Response

- 성공: `204 No Content`
- 응답 본문 없음

현재 로그아웃은 브라우저의 Refresh Cookie를 삭제한다. 이미 발급된 Access Token은 만료 전까지 암호학적으로 유효하므로, 프론트엔드도 보관 중인 Access Token을 함께 삭제해야 한다. 서버에서 즉시 토큰을 폐기하려면 별도의 denylist 또는 세션 저장소가 필요하다.

## 8. 관리자 사용자 목록

### `GET /api/v1/admin/users`

관리자가 전체 사용자를 조회하고 이름·이메일 및 부서로 검색한다.

### Query parameters

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `query` | string | N | 이름 또는 이메일에 포함되는 문자열, 최대 255자 |
| `department` | string | N | `medical`, `dev`, `research` |

```text
GET /api/v1/admin/users?query=user&department=medical
```

### Response: `200 OK`

공통 사용자 응답 객체의 배열을 반환한다. 조회 결과가 없으면 `[]`을 반환한다.

관리자가 아니면 `403 Forbidden`, 인증되지 않았으면 `401 Unauthorized`를 반환한다.

## 9. 관리자 역할 변경

### `PATCH /api/v1/admin/users/role`

관리자가 대상 사용자의 역할을 변경한다.

### Request

```json
{
  "user_id": 7,
  "new_role": "staff"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `user_id` | integer | Y | 역할을 변경할 사용자 ID |
| `new_role` | string | Y | `pending`, `staff`, `admin` |

### Response

- 성공: `200 OK`, 변경된 사용자 객체
- 대상 사용자 없음: `404 Not Found`
- 관리자 본인의 역할 변경 시도: `403 Forbidden`
- 관리자 권한 없음: `403 Forbidden`

관리자 본인의 권한을 변경하지 못하게 하여 운영 중 관리자 권한이 우발적으로 사라지는 상황을 방지한다.

## 10. 내 정보 조회

### `GET /api/v1/users/me`

Access Token으로 식별한 현재 사용자의 정보를 반환한다.

### Response

- 성공: `200 OK`, 공통 사용자 응답 객체
- 인증 실패: `401 Unauthorized`

## 11. 내 정보 수정

### `PATCH /api/v1/users/me`

현재 사용자의 부서와 휴대폰 번호를 부분 수정한다.

### Request

```json
{
  "department": "research",
  "phone_number": "01098765432"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `department` | string | N | 변경할 부서 |
| `phone_number` | string | N | 변경할 휴대폰 번호, 중복 불가 |

입력된 필드만 수정한다. 두 필드를 모두 생략하거나 `null`만 전달하면 `400 Bad Request`, 다른 사용자가 사용 중인 휴대폰 번호이면 `400 Bad Request`를 반환한다.

### Response

- 성공: `200 OK`, 수정된 사용자 객체

## 12. 비밀번호 변경

### `PATCH /api/v1/users/me/password`

기존 비밀번호를 검증한 뒤 새 비밀번호를 Argon2로 해시하여 저장한다.

### Request

```json
{
  "current_password": "Password1!",
  "new_password": "NewPassword2@"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `current_password` | string | Y | 현재 비밀번호 |
| `new_password` | string | Y | 회원가입과 동일한 비밀번호 규칙 적용 |

### Response

- 성공: `204 No Content`
- 기존 비밀번호 불일치 또는 새 비밀번호 규칙 위반: `400 Bad Request`

## 13. 회원 탈퇴

### `DELETE /api/v1/users/me`

현재 사용자를 DB에서 삭제하고 Refresh Cookie를 제거한다.

### Response

- 성공: `204 No Content`
- 응답 본문 없음

사용자와 연결된 데이터의 삭제 또는 `SET NULL` 처리는 실제 DB 외래키 정책을 따른다.

## 14. 인증·인가 정책

Access Token payload에는 최소 식별 정보만 포함한다.

```json
{
  "sub": "5",
  "type": "access",
  "iat": 1784700000,
  "exp": 1784701800
}
```

- Access Token 만료: 30분
- Refresh Token 만료: 7일
- 토큰 서명키는 `.env`의 `JWT_SECRET_KEY`로 관리
- `401`: 요청자를 인증할 수 없음
- `403`: 인증은 되었지만 해당 기능의 권한이 없음
- `pending`: 마이페이지 기능 외 서비스 접근 제한
- `staff`: 내부 업무 기능 사용 가능
- `admin`: 사용자 관리 및 전체 데이터 접근 가능

## 15. 완료 확인 항목

- 회원가입 응답에 비밀번호와 해시가 노출되지 않는다.
- 동일 이메일과 휴대폰 번호의 중복 가입이 거부된다.
- Swagger 로그인에서 이메일은 `username` 필드에 입력한다.
- 로그인 후 Access Token으로 `/users/me`를 조회할 수 있다.
- Refresh Cookie로 Access Token을 갱신할 수 있다.
- 일반 사용자는 관리자 API에서 `403`을 받는다.
- 관리자는 이름·이메일·부서 조건으로 사용자를 조회할 수 있다.
- 관리자는 본인의 역할을 변경할 수 없다.
- 정보 수정은 입력된 필드만 변경한다.
- 로그아웃과 회원 탈퇴 후 클라이언트의 Access Token도 제거한다.
