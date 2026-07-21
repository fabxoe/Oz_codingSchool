# 5일차 환자관리 API 설계

## 1. 문서 목적

이 문서는 stage5 요구사항과 현재 FastAPI·프론트엔드 구현을 기준으로 환자 및 진료기록 API의 계약을 정의한다.

### 공통 기준

| 항목 | 내용 |
| --- | --- |
| API prefix | `/api/v1` |
| 인증 | `Authorization: Bearer <access_token>` |
| JSON 요청 | `application/json` |
| 이미지 포함 요청 | `multipart/form-data` |
| 날짜 형식 | ISO 8601 문자열 |
| 이미지 접근 URL | `/media/xray/<서버가 생성한 파일명>` |

이번 단계의 진료기록 범위는 등록, 환자별 목록 조회, 상세 조회까지다. 진료기록 수정·삭제 및 AI 예측 API는 stage5 범위에 포함하지 않는다.

## 2. 요구사항과 endpoint

| 요구사항 ID | 기능 | Method | Endpoint | 인증·권한 |
| --- | --- | --- | --- | --- |
| REQ-PTNT-001 | 환자 등록 | `POST` | `/api/v1/patients` | `staff`, `admin` |
| REQ-PTNT-002 | 환자 목록·검색·필터 | `GET` | `/api/v1/patients` | 로그인 사용자 |
| REQ-PTNT-003 | 환자 상세 조회 | `GET` | `/api/v1/patients/{patient_id}` | 로그인 사용자 |
| REQ-PTNT-004 | 환자 정보 수정 | `PATCH` | `/api/v1/patients/{patient_id}` | 로그인 사용자 |
| REQ-PTNT-005 | 환자 삭제 | `DELETE` | `/api/v1/patients/{patient_id}` | 로그인 사용자 |
| REQ-MDR-001 | 진료기록·X-Ray 등록 | `POST` | `/api/v1/medical-records` | `staff`, `admin` |
| REQ-MDR-002 | 환자별 진료기록 목록 | `GET` | `/api/v1/patients/{patient_id}/medical-records` | 로그인 사용자 |
| REQ-MDR-003 | 진료기록 상세 조회 | `GET` | `/api/v1/medical-records/{record_id}` | 로그인 사용자 |

## 3. 공통 응답

### 오류 응답

```json
{
  "detail": "존재하지 않는 환자입니다."
}
```

| 상태 코드 | 의미 |
| --- | --- |
| `200 OK` | 조회·수정 성공 |
| `201 Created` | 환자 또는 진료기록 등록 성공 |
| `204 No Content` | 환자 삭제 성공 |
| `400 Bad Request` | 수정 값 누락 또는 허용하지 않는 이미지 형식 |
| `401 Unauthorized` | Access Token 없음, 만료 또는 위조 |
| `403 Forbidden` | 로그인했지만 등록 권한 없음 |
| `404 Not Found` | 환자 또는 진료기록 없음 |
| `409 Conflict` | 진료 차트 번호 중복 |
| `422 Unprocessable Entity` | 필수 필드 누락, 타입·범위·Enum 검증 실패 |

## 4. 환자 응답 객체

```json
{
  "id": 2,
  "name": "david",
  "age": 12,
  "gender": "male",
  "phone_number": "01028932022",
  "created_at": "2026-07-21T18:30:00",
  "updated_at": null
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | integer | 환자 고유 ID |
| `name` | string | 환자 이름 |
| `age` | integer | 환자 나이 |
| `gender` | string | `male` 또는 `female` |
| `phone_number` | string | 환자 연락처 |
| `created_at` | datetime | 등록 일시 |
| `updated_at` | datetime 또는 null | 마지막 수정 일시 |

DB 모델의 컬럼명은 `phone`이지만 API 계약은 프론트엔드에 맞춰 `phone_number`를 사용한다. Service 또는 schema 계층에서 두 이름을 변환한다.

## 5. 환자 등록

### `POST /api/v1/patients`

`staff` 또는 `admin` 역할 사용자가 환자를 등록한다.

### Request

```json
{
  "name": "홍길동",
  "age": 45,
  "gender": "male",
  "phone_number": "01012345678"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `name` | string | Y | 환자 이름, DB 기준 최대 30자 |
| `age` | integer | Y | 0 이상의 나이 |
| `gender` | string | Y | `male`, `female` |
| `phone_number` | string | Y | 휴대폰 번호, DB 기준 최대 11자 |

### Response

- 성공: `201 Created`, 환자 응답 객체
- 인증 실패: `401 Unauthorized`
- `pending` 등 등록 권한이 없는 사용자: `403 Forbidden`
- 요청 검증 실패: `422 Unprocessable Entity`

## 6. 환자 목록 조회

### `GET /api/v1/patients`

환자 목록을 ID 오름차순으로 반환한다. 모든 Query parameter는 선택 사항이며 함께 사용할 수 있다.

### Query parameters

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `name` | string | N | 이름 부분 검색 |
| `gender` | string | N | `male` 또는 `female` |
| `min_age` | integer | N | 결과에 포함할 최소 나이 |
| `max_age` | integer | N | 결과에 포함할 최대 나이 |

```text
GET /api/v1/patients?name=홍&gender=male&min_age=30&max_age=60
```

### Response: `200 OK`

환자 응답 객체의 배열을 반환한다. 결과가 없으면 `[]`을 반환한다.

```json
[
  {
    "id": 1,
    "name": "홍길동",
    "age": 45,
    "gender": "male",
    "phone_number": "01012345678",
    "created_at": "2026-07-20T10:00:00",
    "updated_at": null
  }
]
```

`min_age`가 `max_age`보다 큰 요청에 대한 별도 업무 규칙은 현재 정의되어 있지 않으며, 두 조건을 모두 적용한 빈 배열이 반환될 수 있다.

## 7. 환자 상세 조회

### `GET /api/v1/patients/{patient_id}`

### Path parameter

| 이름 | 타입 | 규칙 | 설명 |
| --- | --- | --- | --- |
| `patient_id` | integer | 1 이상 | 조회할 환자 ID |

### Response

- 성공: `200 OK`, 환자 응답 객체
- 환자 없음: `404 Not Found`
- Path parameter 검증 실패: `422 Unprocessable Entity`

## 8. 환자 정보 수정

### `PATCH /api/v1/patients/{patient_id}`

이름과 연락처 중 요청에 포함된 필드만 수정한다. 나이와 성별은 이번 요구사항에서 수정 대상이 아니다.

### Request

```json
{
  "name": "홍길순",
  "phone_number": "01098765432"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `name` | string | N | 수정할 환자 이름 |
| `phone_number` | string | N | 수정할 연락처 |

### Response

- 성공: `200 OK`, 수정된 환자 응답 객체
- 두 필드를 모두 생략: `400 Bad Request`
- 환자 없음: `404 Not Found`

## 9. 환자 삭제

### `DELETE /api/v1/patients/{patient_id}`

환자를 삭제한다. `medical_records.patient_id`와 `xray_images.record_id`의 `ON DELETE CASCADE`를 통해 연결된 진료기록과 X-Ray DB 정보도 함께 삭제한다.

### Response

- 성공: `204 No Content`
- 응답 본문 없음
- 환자 없음: `404 Not Found`

DB row의 연쇄 삭제와 서버 로컬 디스크에 저장된 실제 이미지 파일 삭제는 서로 다른 작업이다. 요구사항대로 완전히 삭제하려면 DB 삭제 전에 연결된 이미지 경로를 수집하여 실제 파일도 제거해야 한다.

## 10. 진료기록 등록

### `POST /api/v1/medical-records`

`staff` 또는 `admin` 역할 사용자가 진료기록과 X-Ray 이미지를 함께 등록한다.

### Request

`Content-Type: multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `patient_id` | integer | Y | 연결할 환자 ID, 1 이상 |
| `chart_number` | string | Y | 진료 차트 번호, 최대 50자, 중복 불가 |
| `symptoms` | string | Y | 진료된 증상 |
| `xray_image` | file | Y | X-Ray 이미지 파일 |
| `shooting_datetime` | datetime | N | 촬영 일시, 생략하면 서버 현재 시각 사용 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/medical-records \
  -H 'Authorization: Bearer <access_token>' \
  -F 'patient_id=2' \
  -F 'chart_number=CHART-20260722-001' \
  -F 'symptoms=기침과 흉부 통증' \
  -F 'xray_image=@test.png'
```

허용 확장자는 `.jpg`, `.jpeg`, `.png`다. 서버는 UUID 기반 파일명을 생성하고 `media/xray/`에 저장한다. 현재 구현은 확장자를 기준으로 검사하므로, 실무에서는 MIME type과 파일 내용을 추가로 검사해야 한다.

### Response: `201 Created`

```json
{
  "id": 10,
  "patient_id": 2,
  "chart_number": "CHART-20260722-001",
  "symptoms": "기침과 흉부 통증",
  "xray_image_url": "/media/xray/3d05de0d4c8a4cdc8a0678cc3aa9e29c.png",
  "created_at": "2026-07-22T10:10:00"
}
```

### 실패 응답

| 상황 | 상태 코드 |
| --- | --- |
| 환자 없음 | `404 Not Found` |
| 차트 번호 중복 | `409 Conflict` |
| 허용하지 않는 확장자 | `400 Bad Request` |
| 필수 form 또는 file 누락 | `422 Unprocessable Entity` |
| 등록 권한 없음 | `403 Forbidden` |

## 11. 환자별 진료기록 목록 조회

### `GET /api/v1/patients/{patient_id}/medical-records`

대상 환자의 진료기록을 생성일시 최신순으로 반환한다.

### Response: `200 OK`

```json
[
  {
    "id": 10,
    "chart_number": "CHART-20260722-001",
    "symptoms": "기침과 흉부 통증",
    "created_at": "2026-07-22T10:10:00"
  }
]
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | integer | 진료기록 ID |
| `chart_number` | string | 진료 차트 번호 |
| `symptoms` | string | 증상 원문 |
| `created_at` | datetime | 등록 일시 |

증상 100자 초과 시 말줄임표로 표시하는 것은 프론트엔드의 화면 표현 책임이다. API는 원문을 반환한다. 환자가 없으면 `404 Not Found`를 반환한다.

## 12. 진료기록 상세 조회

### `GET /api/v1/medical-records/{record_id}`

진료기록과 연결된 X-Ray 이미지 URL을 반환한다.

### Response: `200 OK`

```json
{
  "id": 10,
  "patient_id": 2,
  "chart_number": "CHART-20260722-001",
  "symptoms": "기침과 흉부 통증",
  "xray_image_url": "/media/xray/3d05de0d4c8a4cdc8a0678cc3aa9e29c.png",
  "created_at": "2026-07-22T10:10:00"
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | integer | 진료기록 ID |
| `patient_id` | integer | 연결된 환자 ID |
| `chart_number` | string | 진료 차트 번호 |
| `symptoms` | string | 증상 원문 |
| `xray_image_url` | string 또는 null | 브라우저에서 접근 가능한 이미지 URL |
| `created_at` | datetime | 등록 일시 |

진료기록이 없으면 `404 Not Found`를 반환한다. 이미지 URL은 API host와 결합하여 접근한다.

```text
http://127.0.0.1:8000/media/xray/<파일명>
```

## 13. 권한 정책

| 역할 | 환자 조회 | 환자 등록 | 환자 수정·삭제 | 진료기록 등록 | 진료기록 조회 |
| --- | --- | --- | --- | --- | --- |
| 비로그인 | 불가 | 불가 | 불가 | 불가 | 불가 |
| `pending` | 가능 | 불가 | 가능 | 불가 | 가능 |
| `staff` | 가능 | 가능 | 가능 | 가능 | 가능 |
| `admin` | 가능 | 가능 | 가능 | 가능 | 가능 |

이 표는 현재 stage5 명세와 구현 기준이다. 4일차 요구사항의 “pending은 마이페이지 외 접근 불가” 정책을 전체 프로젝트에 엄격히 적용하려면 환자 조회·수정·삭제에도 별도의 역할 검사를 추가해야 한다.

## 14. 데이터 처리 흐름

### 환자 등록

```text
HTTP JSON -> Patient schema -> Patient service
-> phone_number를 Patient.phone으로 변환 -> repository -> DB
```

### 진료기록 등록

```text
권한 확인 -> 환자 존재 확인 -> 차트 번호 중복 확인
-> 이미지 확장자 확인 -> 로컬 파일 저장
-> MedicalRecord 생성 및 flush -> XrayImage 생성
-> commit -> 이미지 URL이 포함된 응답
```

## 15. 완료 확인 항목

- `pending` 사용자의 환자·진료기록 등록이 `403`으로 거부된다.
- `staff` 또는 `admin` 사용자가 환자를 등록할 수 있다.
- 이름·성별·최소 나이·최대 나이 필터를 조합할 수 있다.
- 존재하지 않는 환자와 진료기록 조회 시 `404`가 반환된다.
- 환자 수정 시 입력된 필드만 변경된다.
- 빈 PATCH 요청은 `400`으로 거부된다.
- 환자 삭제 후 연결된 진료기록과 X-Ray DB row가 삭제된다.
- `.jpg`, `.jpeg`, `.png` 이미지를 포함한 진료기록을 등록할 수 있다.
- 중복 차트 번호는 `409`로 거부된다.
- 상세 응답의 `xray_image_url`을 브라우저에서 열 수 있다.
- 진료기록 목록은 최신순이며 증상 원문을 반환한다.
