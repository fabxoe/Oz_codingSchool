# 6일차 폐렴예측 API 설계

## 0. 요구사항 매핑

| 요구사항 ID | 내용 | 반영 위치 |
| --- | --- | --- |
| REQ-PRED-001 | 진료기록 상세 페이지에서 AI 예측 결과를 확인할 수 있어야 한다. 이미 같은 모델로 저장된 결과가 있으면 재추론하지 않는다. | 1. 폐렴 예측 요청 API |
| REQ-PRED-002 | 진료기록 상세 페이지의 AI 예측 결과 섹션에서 예측 결과를 목록으로 확인할 수 있어야 한다. | 3. 폐렴 예측 결과 목록 조회 API |
| NFR-PRED-001 | Recall ≥ 0.90, Accuracy ≥ 0.80 | 사용 모델(pneumonia_ensemble_v1)의 EXP-56 파이프라인 기준 public score 0.9583, meta-CV accuracy 약 0.9866으로 Accuracy 기준은 충족. Recall(민감도) 단독 수치는 별도로 재현·검증이 필요함 |
| NFR-PRED-002 | 모든 API는 3초 이내에 응답해야 한다 | 예측 요청 API를 비동기(큐+폴링) 구조로 설계하여 충족 |

### 0.1 NFR-PRED-002 대응 방식

실제 추론(ConvNeXt-Tiny 5-fold + EfficientNet-B0 5-fold 앙상블)은 CPU 기준 약 3.6~5초가 걸려, 요청-응답 사이클 안에서 바로 추론하면 3초 기준을 지킬 수 없다. 그래서 예측 요청과 실제 추론을 분리했다.

```
클라이언트                API 서버                      백그라운드 작업
    │                        │                                │
    │─ POST .../predictions ─►                                │
    │                        │─ 캐시 확인 ──┐                  │
    │                        │              │                  │
    │            (캐시 있음) │◄─────────────┘                  │
    │◄── 200 OK + 결과 ───────│                                │
    │                        │                                │
    │            (캐시 없음) │─ job 등록 + 백그라운드 실행 시작 ─►│
    │◄── 202 Accepted + job_id ─│                              │
    │                        │                          (추론 진행, 3~5초)
    │─ GET .../jobs/{job_id} ─►                                │
    │◄── status: processing ──│                                │
    │        (반복 폴링)      │                                │
    │─ GET .../jobs/{job_id} ─►                                │
    │◄── status: done + 결과 ─│◄───────── 결과 저장 완료 ────────│
```

## 1. 폐렴 예측 요청

### 1) API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 폐렴 예측 요청 API |
| 설명 | 진료기록의 X-ray 이미지로 폐렴 예측을 요청한다. 이미 같은 모델로 예측한 결과가 있으면 재추론 없이 즉시 반환한다. |
| 엔드포인트(Endpoint) | `/api/v1/medical-records/{record_id}/predictions` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | Y (STAFF, ADMIN만 가능) |

### 2) 요청(Request)

**Headers**
| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 필수 |

**Path 파라미터**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| record_id | integer | 예측 대상 진료기록 ID |

본문 없음. (X-ray 이미지는 새로 업로드하지 않고, 해당 진료기록 등록 시 저장된 이미지를 그대로 사용한다.)

### 3) 응답(Response)

**성공 — 캐시된 결과가 있는 경우**
- 200 OK
```json
{
  "status": "done",
  "cached": true,
  "result": {
    "id": 12,
    "record_id": 7,
    "is_pneumonia": true,
    "confidence": 0.9821,
    "heatmap_url": null,
    "ai_model": "pneumonia_ensemble_v1",
    "created_at": "2026-07-22T10:00:00"
  }
}
```

**성공 — 새로 추론이 필요한 경우**
- 202 Accepted
```json
{
  "status": "queued",
  "cached": false,
  "job_id": "a1b2c3d4e5f6...",
  "poll_url": "/api/v1/predictions/jobs/a1b2c3d4e5f6..."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| status | string | `done`(캐시 반환) 또는 `queued`(백그라운드 작업 등록됨) |
| cached | boolean | 재추론 없이 저장된 결과를 반환했는지 여부 |
| result | object \| null | 예측 결과. `status=done`일 때만 값이 있음 |
| job_id | string \| null | 백그라운드 작업 ID. `status=queued`일 때만 값이 있음 |
| poll_url | string \| null | 작업 상태를 확인할 수 있는 URL |

**실패**
- 401 Unauthorized — 인증 안 됨
- 403 Forbidden — STAFF/ADMIN이 아님
- 404 Not Found — 존재하지 않는 진료기록
```json
{ "detail": "존재하지 않는 진료기록입니다." }
```
- 422 Unprocessable Entity — 해당 진료기록에 X-ray 이미지가 없음
```json
{ "detail": "해당 진료기록에 X-ray 이미지가 없어 예측할 수 없습니다." }
```

### 4) 비고
- 동시에 같은 진료기록에 대해 여러 번 요청이 들어와도, 이미 진행 중인 작업이 있으면 새로 작업을 만들지 않고 기존 `job_id`를 그대로 돌려준다. (중복 추론 방지)
- 캐시 판단 기준은 "같은 `record_id` + 같은 `ai_model`"이다. 모델 버전이 바뀌면 재추론된다.

---

## 2. 예측 작업 상태 조회 (폴링)

### 1) API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 예측 작업 상태 조회 API |
| 설명 | 예측 요청 시 받은 `job_id`로 백그라운드 추론 진행 상태를 확인한다. |
| 엔드포인트(Endpoint) | `/api/v1/predictions/jobs/{job_id}` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y (STAFF, ADMIN만 가능) |

### 2) 요청(Request)

**Path 파라미터**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| job_id | string | 예측 요청 API 응답으로 받은 작업 ID |

### 3) 응답(Response)

**성공**
- 200 OK
```json
{
  "job_id": "a1b2c3d4e5f6...",
  "record_id": 7,
  "status": "done",
  "result": {
    "id": 12,
    "record_id": 7,
    "is_pneumonia": true,
    "confidence": 0.9821,
    "heatmap_url": null,
    "ai_model": "pneumonia_ensemble_v1",
    "created_at": "2026-07-22T10:00:00"
  },
  "error": null
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| status | string | `queued`(대기) → `processing`(추론 중) → `done`(완료) 또는 `failed`(실패) |
| result | object \| null | `status=done`일 때만 값이 있음 |
| error | string \| null | `status=failed`일 때 실패 사유 |

**실패**
- 404 Not Found — 존재하지 않거나 서버 재시작으로 만료된 작업
```json
{ "detail": "존재하지 않거나 만료된 작업입니다." }
```

### 4) 비고
- 작업 상태는 서버 프로세스의 메모리에 저장되므로, 서버가 재시작되면 진행 중이던 작업 정보는 사라진다. 이 경우 클라이언트는 예측 요청 API를 다시 호출해야 한다.
- 프론트엔드는 `status`가 `done` 또는 `failed`가 될 때까지 일정 간격(예: 1~2초)으로 이 API를 반복 호출(폴링)한다.

---

## 3. 폐렴 예측 결과 목록 조회

### 1) API 개요
| 항목 | 내용 |
| --- | --- |
| API 이름 | 폐렴 예측 결과 목록 조회 API |
| 설명 | 진료기록의 X-ray 이미지와, 그동안 수행된 모든 예측 결과를 목록으로 조회한다. |
| 엔드포인트(Endpoint) | `/api/v1/medical-records/{record_id}/predictions` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y (STAFF, ADMIN만 가능) |

### 2) 요청(Request)

**Path 파라미터**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| record_id | integer | 진료기록 ID |

### 3) 응답(Response)

**성공**
- 200 OK
```json
{
  "record_id": 7,
  "xray_image_url": "/media/xray/7_example.jpg",
  "predictions": [
    {
      "id": 12,
      "is_pneumonia": true,
      "confidence": 0.9821,
      "heatmap_url": null,
      "ai_model": "pneumonia_ensemble_v1",
      "created_at": "2026-07-22T10:00:00"
    }
  ]
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| xray_image_url | string \| null | 해당 진료기록의 X-ray 이미지 URL |
| predictions | array | 예측 결과 목록 (최신순). 고유 ID, 폐렴 여부, confidence, heatmap URL, 예측 일시, 사용 모델 포함 (REQ-PRED-002) |

**실패**
- 404 Not Found — 존재하지 않는 진료기록

### 4) 비고
- 같은 진료기록에 대해 여러 모델 버전으로 예측한 이력이 있다면, 모두 목록에 나타난다.

---

## 4. 공통 사항

- 모든 API는 `STAFF` 또는 `ADMIN` role만 접근 가능하다. (사내 의료인, 개발팀, 연구자에 해당)
- `confidence`는 소수점 4자리까지 저장한다. (`Numeric(5,4)`)
- 현재 사용 모델(`pneumonia_ensemble_v1`)은 히트맵 이미지를 생성하지 않으므로 `heatmap_url`은 항상 `null`이다. 추후 히트맵을 지원하는 모델로 교체되면 값이 채워질 수 있다.
- 인증 실패는 401, 권한 부족은 403으로 구분한다.
- 현재 사용 모델(`pneumonia_ensemble_v1`)은 EXP-56 파이프라인 기준 public score 0.9583, meta-CV accuracy 약 0.9866으로 Accuracy 요건(≥0.80)은 충족하는 것으로 확인된다. 다만 NFR-PRED-001이 요구하는 Recall(민감도, ≥0.90) 단독 수치는 팀장님이 공유한 자료에 명시되어 있지 않아, 별도로 confusion matrix를 뽑아 확인이 필요하다.