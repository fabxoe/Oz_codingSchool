# User API 설계

## 1. 회원가입

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원가입 API |
| 설명 | 이메일, 비밀번호 등을 입력하여 신규 계정을 생성한다 |
| 엔드포인트(Endpoint) | `/api/v1/auth/signup` |
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
  "password": "securepassword",
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
| password | string | Y | 비밀번호 (서버에서 해시하여 저장) |
| name | string | Y | 이름 |
| department | string | Y | 부서. `MEDICAL`, `DEV`, `RESEARCH` 중 하나 |
| gender | string | Y | 성별. `M`, `F` 중 하나 |
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
| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 생성된 사용자 고유 ID |
| role | string | 가입 직후 기본값은 `PENDING` (대기자) |
| is_active | boolean | 계정 활성화 여부, 가입 시 기본 `true` |

**실패**
- 400 Bad Request
```json
{ "detail": "invalid_email_format" }
```
- 409 Conflict
```json
{ "detail": "email_already_exists" }
```
| 필드명 | 설명 |
| --- | --- |
| invalid_email_format | 이메일 형식이 올바르지 않은 경우 |
| empty_fields | 필수 필드 중 비어있는 값이 있는 경우 |
| email_already_exists | 이미 가입된 이메일인 경우 |
| phone_number_already_exists | 이미 등록된 휴대폰 번호인 경우 |

### 4. 비고
- 가입 시 `role`은 무조건 `PENDING`으로 시작하며, Admin이 권한을 변경해줘야 서비스를 이용할 수 있다. (REQ-USER-001, REQ-USER-005)
- 비밀번호는 평문 저장 금지, 해시(예: bcrypt)로 저장한다.

---

## 2. 로그인

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 로그인 API |
| 설명 | 이메일, 비밀번호를 통해 로그인하고 JWT를 발급받는다 |
| 엔드포인트(Endpoint) | `/api/v1/auth/login` |
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
  "password": "securepassword"
}
```

**본문 필드**
| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 사용자 이메일 |
| password | string | Y | 사용자 비밀번호 |

### 3. 응답(Response)

**성공**
- 200 OK
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "example@example.com",
    "name": "홍길동",
    "role": "STAFF"
  }
}
```
| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| access_token | string | JWT 액세스 토큰 (만료 30분). 페이로드에는 `user_id`만 포함 |
| token_type | string | 고정값 `bearer` |
| user | object | 로그인한 사용자 요약 정보 |

추가로 **Set-Cookie** 헤더를 통해 `refresh_token`을 `http_only` 쿠키로 전달한다 (만료 7일, body에는 포함하지 않음).

**실패**
- 400 Bad Request
```json
{ "detail": "invalid_email_or_password" }
```
| 필드명 | 설명 |
| --- | --- |
| invalid_email_or_password | 이메일 혹은 비밀번호가 잘못된 경우 |
| empty_fields | 필수 필드 중 비어있는 값이 있는 경우 |
| inactive_account | 비활성화된 계정으로 로그인 시도한 경우 |

### 4. 비고
- 리프레시 토큰은 XSS 공격 방지를 위해 클라이언트 JS에서 접근 불가능한 `http_only` 쿠키로만 전달한다. (NFR-USER-001)
- JWT 페이로드에는 `user_id` 외 다른 개인정보를 포함하지 않는다.

---

## 3. 토큰 재발급

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 액세스 토큰 재발급 API |
| 설명 | 만료된 액세스 토큰을 리프레시 토큰으로 재발급받는다 |
| 엔드포인트(Endpoint) | `/api/v1/auth/refresh` |
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
| refresh_token_invalid | 위변조되었거나 유효하지 않은 토큰인 경우 |

### 4. 비고
- 리프레시 토큰까지 만료된 경우 클라이언트는 로그인 페이지로 리다이렉트한다. (NFR-USER-001)

---

## 4. 로그아웃

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 로그아웃 API |
| 설명 | 현재 세션을 종료하고 리프레시 토큰 쿠키를 만료시킨다 |
| 엔드포인트(Endpoint) | `/api/v1/auth/logout` |
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

응답 본문 없음. `Set-Cookie`로 `refresh_token`을 즉시 만료시켜 클라이언트에서 제거되도록 한다.

**실패**
- 401 Unauthorized
```json
{ "detail": "unauthorized" }
```

### 4. 비고
- 로그아웃 후 클라이언트는 로그인 페이지로 전환한다. (REQ-USER-003)

---

## 5. 회원 목록 조회 (Admin 전용)

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 목록 조회 API |
| 설명 | Admin 권한 유저가 전체 회원 목록을 검색/필터하여 조회한다 |
| 엔드포인트(Endpoint) | `/api/v1/users` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y (Admin 권한 필요) |

### 2. 요청(Request)

**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |

**쿼리 파라미터**
| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| keyword | string | N | 이메일 또는 이름으로 검색 |
| department | string | N | 부서 필터. `MEDICAL`, `DEV`, `RESEARCH` |
| page | integer | N | 페이지 번호 (기본값 1) |
| size | integer | N | 페이지당 개수 (기본값 20) |

### 3. 응답(Response)

**성공**
- 200 OK
```json
{
  "total": 42,
  "page": 1,
  "size": 20,
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
| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| total | integer | 전체 회원 수 |
| items | array | 회원 목록. 요구사항의 고유ID, 이메일, 이름, 부서, 성별, 휴대폰번호, 활성화 여부 포함 |

**실패**
- 403 Forbidden
```json
{ "detail": "admin_permission_required" }
```

### 4. 비고
- Admin 권한이 아닌 유저가 호출할 경우 403을 반환한다. (REQ-USER-004)

---

## 6. 회원 권한 변경 (Admin 전용)

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 권한 변경 API |
| 설명 | Admin 권한 유저가 특정 회원의 role을 변경한다 |
| 엔드포인트(Endpoint) | `/api/v1/users/{user_id}/role` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y (Admin 권한 필요) |

### 2. 요청(Request)

**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |
| Content-Type | application/json | 요청 타입 |

**Path 파라미터**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| user_id | integer | 권한을 변경할 대상 회원의 ID |

**본문 예시**
```json
{
  "role": "STAFF"
}
```

**본문 필드**
| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
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
{ "detail": "invalid_role" }
```

### 4. 비고
- 대기자(PENDING)는 마이페이지 외 모든 기능 접근이 불가하며, 스태프/어드민 승격은 이 API로만 가능하다. (REQ-USER-005)

---

## 7. 마이페이지 조회

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

본문 없음.

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

### 4. 비고
- 응답 필드는 요구사항의 이름, 이메일, 부서, 성별, 휴대폰 번호, 권한으로 한정한다. (REQ-USER-006)

---

## 8. 회원 정보 수정

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 내 정보 수정 API |
| 설명 | 로그인한 유저 본인의 부서, 휴대폰 번호를 부분 수정한다 |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

### 2. 요청(Request)

**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |
| Content-Type | application/json | 요청 타입 |

**본문 예시**
```json
{
  "phone_number": "01099998888"
}
```

**본문 필드**
| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| department | string | N | `MEDICAL`, `DEV`, `RESEARCH` 중 하나 |
| phone_number | string | N | 휴대폰 번호 (중복 불가) |

두 필드 모두 선택이며, 보낸 필드만 수정된다 (Partial Update).

### 3. 응답(Response)

**성공**
- 200 OK
```json
{
  "id": 1,
  "department": "MEDICAL",
  "phone_number": "01099998888",
  "updated_at": "2026-07-16T10:30:00"
}
```

**실패**
- 400 Bad Request
```json
{ "detail": "no_fields_to_update" }
```
- 409 Conflict
```json
{ "detail": "phone_number_already_exists" }
```

### 4. 비고
- 수정 가능한 항목은 부서, 휴대폰 번호로 한정한다. 이메일/이름/성별 등은 이 API로 변경 불가하다. (REQ-USER-007)

---

## 9. 비밀번호 변경

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 비밀번호 변경 API |
| 설명 | 로그인한 유저 본인의 비밀번호를 변경한다 |
| 엔드포인트(Endpoint) | `/api/v1/users/me/password` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

### 2. 요청(Request)

**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |
| Content-Type | application/json | 요청 타입 |

**본문 예시**
```json
{
  "current_password": "oldpassword123",
  "new_password": "newpassword456"
}
```

**본문 필드**
| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| current_password | string | Y | 기존 비밀번호, 일치 여부 검증용 |
| new_password | string | Y | 새로운 비밀번호 |

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
| new_password_same_as_current | 새 비밀번호가 기존 비밀번호와 동일한 경우 |
| weak_password | 새 비밀번호가 정책(최소 길이 등)을 만족하지 못하는 경우 |

### 4. 비고
- 기존 비밀번호 검증에 성공한 경우에만 변경을 적용한다. (REQ-USER-008)
- 프론트엔드는 비밀번호 입력 필드를 마스킹 처리하고, 보기 아이콘으로 토글 가능해야 한다. (NFR-USER-002)

---

## 10. 회원 탈퇴

### 1. API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 탈퇴 API |
| 설명 | 로그인한 유저 본인 계정 및 관련 정보를 즉시 삭제한다 |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `DELETE` |
| 인증 필요 여부 | Y |

### 2. 요청(Request)

**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |
| Content-Type | application/json | 요청 타입 |

**본문 예시**
```json
{
  "password": "securepassword"
}
```

**본문 필드**
| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| password | string | Y | 본인 확인용 현재 비밀번호 |

### 3. 응답(Response)

**성공**
- 204 No Content

**실패**
- 400 Bad Request
```json
{ "detail": "password_mismatch" }
```

### 4. 비고
- 탈퇴 시 해당 유저 관련 정보는 DB에서 즉시 하드 삭제(hard delete)한다. (REQ-USER-009)
- FK로 연결된 데이터(예: xray_images.uploader_id) 는 모델 설계상 `ON DELETE SET NULL`이 적용되어 있어, 유저 삭제 후에도 업로드 이력 자체는 남는다.

---

## 공통 사항

- 모든 API는 요청 처리 후 3초 이내에 응답해야 한다. (NFR-USER-003)
- 인증이 필요한 API는 `Authorization: Bearer <access_token>` 헤더가 없거나 유효하지 않으면 401을 반환한다.
- Admin 전용 API를 Admin이 아닌 유저가 호출하면 403을 반환한다.
