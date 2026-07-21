# 6일차 - AI 폐렴 예측 API 설계

작성자: 권일준
관련 요구사항: REQ-PRED-001, REQ-PRED-002, NFR-PRED-001, NFR-PRED-002

---

## 0. 공통 규약

### Base URL

```
/api/v1
```

### 인증

모든 예측 API는 로그인이 필요하다. `Authorization: Bearer <Access Token>` 헤더를 사용한다.

### 권한

요구사항의 "사내 의료인, 개발팀, 연구자"는 `Department` 값(`medical`, `dev`, `research`)에 해당한다.
현재 구현된 `Role` 은 `pending` / `staff` / `admin` 세 가지이며, 승인 전 사용자(`pending`)를 걸러내는 역할을 한다.

따라서 예측 API의 권한 기준은 **`role in (staff, admin)`** 으로 한다.
`department` 는 승인 시점에 이미 부여되므로 별도 검사하지 않는다.

| 상황 | 응답 |
|---|---|
| 토큰 없음 / 만료 / 위조 | `401 Unauthorized` |
| `role == pending` | `403 Forbidden` |

### 에러 응답 형식

```json
{ "detail": "에러 메시지" }
```

| 코드 | 의미 |
|---|---|
| 400 | 요청 값이 잘못됨 |
| 401 | 인증 실패 |
| 403 | 권한 없음 |
| 404 | 대상 없음 |
| 409 | 이미 처리 중인 작업이 있음 |
| 422 | 예측 불가 (X-ray 이미지 없음 등) |

---

## 1. 사용 모델

| 항목 | 값 |
|---|---|
| 식별자 | `pneumonia_ensemble_v1` |
| 구조 | ConvNeXt-Tiny 5-fold + EfficientNet-B0 5-fold → RidgeClassifier |
| 입력 | RGB, 224×224, ImageNet mean/std 정규화 |
| 판정 | `decision_score >= 0.025` 이면 폐렴 |
| 출력 | `is_pneumonia`, `confidence`, `decision_score`, `model` |

### NFR-PRED-001 (모델 평가 기준) 충족 여부

| 기준 | 요구 | 모델 | 판정 |
|---|---|---|---|
| Accuracy | ≥ 0.80 ~ 0.90 | meta-CV 약 0.9866 | ✅ |
| Recall (민감도) | ≥ 0.90 | **미측정** | ⚠️ |

<br>

> **Recall은 별도 측정이 필요하다.**
> 모델 문서에 기록된 값은 public score와 meta-CV accuracy뿐이다.
> Recall은 "실제 폐렴 환자를 놓치지 않는가"를 보는 지표이고, FN(폐렴인데 정상 판정)이
> 가장 위험한 오류이므로 서비스 배포 전 검증 항목으로 남긴다.

---

## 2. 아키텍처

### 왜 API 서버에서 직접 추론하지 않는가

1. **모델은 thread-safe 하지 않다.** 10개 모델 인스턴스를 여러 요청이 동시에 쓰면 내부 상태가 섞인다.
2. **추론이 CPU를 오래 점유한다.** FastAPI 프로세스 안에서 돌리면 그동안 다른 요청 처리가 밀린다.
3. **모델 로딩에 메모리가 크게 든다.** API 서버를 여러 개 띄울 때마다 609MB를 중복 적재하게 된다.

### 구조

```
[Client]
   │  ① POST 예측 요청
   ▼
[FastAPI] ──② job 등록(Redis)──▶ [Redis]
   │                                 │
   │  ③ 202 + job_id                 │ ④ BLPOP
   ▼                                 ▼
[Client]                        [Worker] (모델 독점)
   │                                 │
   │  ⑥ GET job 상태 폴링             │ ⑤ 추론 → DB 저장 → job 상태 갱신
   ▼                                 ▼
[FastAPI] ◀──────────────────── [Redis] / [MySQL]
```

| 요소 | 역할 |
|---|---|
| FastAPI | 요청 검증, 캐시 조회, 작업 등록, 상태·결과 조회 |
| Redis | 작업 대기열(List) + 작업 상태 저장(Hash) |
| Worker | 모델 로드(1회), 추론, DB 저장, 상태 갱신 |
| MySQL | 예측 결과 영구 저장 (`ai_analysis_results`) |

### Redis 키 설계

| 키 | 타입 | 용도 | TTL |
|---|---|---|---|
| `pneumonia:queue` | List | 작업 대기열 (`RPUSH` / `BLPOP`) | — |
| `pneumonia:job:{job_id}` | Hash | 작업 상태 | 1시간 |
| `pneumonia:lock:{record_id}` | String | 같은 진료기록 중복 요청 방지 | 10분 |

`pneumonia:job:{job_id}` 필드:

```
status         queued | processing | done | failed
record_id      진료기록 ID
result_id      완료 시 ai_analysis_results.id
error          실패 시 메시지
created_at     요청 시각
```

---

## 3. 응답 방식 — 왜 비동기(202)인가

### 배경

NFR-PRED-002는 **모든 API가 3초 이내 응답**을 요구한다.
그러나 모델 문서 8절에 기록된 CPU 추론 시간은 다음과 같다.

| 구성 | 시간 |
|---|---|
| ConvNeXt-Tiny 1개 | 약 0.42초 |
| EfficientNet-B0 5개 | 약 0.82초 |
| **전체 10개 모델** | **약 3.6 ~ 5.0초** |

여기에 큐 대기와 Redis 왕복이 더해지므로, 결과를 기다렸다 응답하는 방식으로는 3초를 지킬 수 없다.

### 선택

**모델 정확도를 유지하기 위해 10개 모델 구성을 그대로 사용하고, 대신 API를 비동기로 설계한다.**

| 방식 | 3초 충족 | 정확도 | 채택 |
|---|---|---|---|
| 동기 대기 | ❌ (3.6~5초) | 유지 | |
| fold 축소 (10→2) | ✅ | 하락, 재검증 필요 | |
| **비동기 (202 + 폴링)** | **✅** | **유지** | **✅** |

예측 요청 API는 작업을 등록하고 **즉시 `202 Accepted`** 를 반환한다.
모든 API가 3초 이내에 응답하므로 NFR-PRED-002를 충족한다.

### REQ-PRED-001의 "바로 확인" 문구와의 관계

프론트엔드는 `AI 예측 결과보기` 클릭 시 로딩 상태를 표시하고, 작업 상태 API를 **1초 간격으로 폴링**하다가 완료되면 결과 섹션에 렌더링한다. 사용자 관점에서는 한 번의 클릭으로 결과를 보게 되므로 요구사항을 만족한다.

**캐시된 결과가 있으면 폴링 없이 즉시 `200`으로 반환**되므로, 두 번째 조회부터는 대기가 없다.

---

## 4. DB 스키마 변경

기존 `ai_analysis_results` 테이블을 사용하되 두 컬럼을 수정한다.

| 컬럼 | 변경 전 | 변경 후 | 사유 |
|---|---|---|---|
| `heatmap_url` | `String(255) NOT NULL` | `String(255) NULL` | 요구사항에 "선택사항"으로 명시. 현재 모델은 히트맵을 생성하지 않는다 |
| `confidence` | `Numeric(5, 2)` | `Numeric(5, 4)` | 모델이 반환하는 `0.9821`이 `0.98`로 잘려 정밀도가 손실된다 |

<br>

나머지 컬럼은 요구사항과 그대로 일치하므로 변경하지 않는다.

| 요구사항 항목 | 컬럼 |
|---|---|
| 고유 ID | `id` |
| 폐렴 여부 | `is_pneumonia` |
| Confidence | `confidence` |
| Hitmap Image URL | `heatmap_url` |
| 예측 수행 일시 | `created_at` |
| 사용한 모델 | `ai_model` |

---

## 5. 캐싱 정책

> REQ-PRED-001: "이미 해당 진료기록으로 같은 모델을 사용하여 저장된 예측 결과가 있다면
> 별도로 AI 추론 과정을 거치지 않고 저장되어 있던 데이터를 응답한다."

**조회 조건**: `record_id == ? AND ai_model == 'pneumonia_ensemble_v1'`

| 케이스 | 동작 | 응답 |
|---|---|---|
| 결과 있음 | 추론하지 않고 기존 결과 반환 | `200 OK` + 결과 |
| 결과 없음 | 큐에 작업 등록 | `202 Accepted` + `job_id` |
| 같은 진료기록이 이미 처리 중 | 기존 작업의 `job_id` 반환 | `202 Accepted` + `job_id` |

세 번째 케이스는 `pneumonia:lock:{record_id}` 키로 판별한다. 사용자가 버튼을 연타해도 같은 이미지를 여러 번 추론하지 않는다.

모델을 교체하면 `ai_model` 값이 달라지므로 자동으로 새로 추론된다. 별도 무효화 로직이 필요 없다.

---

## 6. API 명세

### 6-1. 폐렴 예측 요청

REQ-PRED-001

| | |
|---|---|
| 메서드 | `POST` |
| 경로 | `/api/v1/medical-records/{record_id}/predictions` |
| 권한 | `staff`, `admin` |

**Path Parameter**

| 이름 | 타입 | 제약 |
|---|---|---|
| `record_id` | integer | ≥ 1 |

**Request Body** — 없음

예측에 사용할 X-ray 이미지는 진료기록 저장 시 업로드된 것을 서버가 조회해 사용한다.

**Response — 200 OK** (캐시된 결과가 있는 경우)

```json
{
  "status": "done",
  "cached": true,
  "result": {
    "id": 12,
    "record_id": 5,
    "is_pneumonia": true,
    "confidence": 0.9821,
    "heatmap_url": null,
    "ai_model": "pneumonia_ensemble_v1",
    "created_at": "2026-07-21T14:03:11"
  }
}
```

**Response — 202 Accepted** (새로 추론이 필요한 경우)

```json
{
  "status": "queued",
  "cached": false,
  "job_id": "9f2c1b7e4a5d4f0e8c3a6b1d2e5f7a90",
  "poll_url": "/api/v1/predictions/jobs/9f2c1b7e4a5d4f0e8c3a6b1d2e5f7a90"
}
```

**에러**

| 코드 | 조건 |
|---|---|
| 401 | 인증되지 않은 사용자 |
| 403 | `role == pending` |
| 404 | 존재하지 않는 진료기록 |
| 422 | 해당 진료기록에 X-ray 이미지가 없음 |
| 503 | 큐(Redis) 연결 실패 |

<br>

---

### 6-2. 예측 작업 상태 조회

REQ-PRED-001 (비동기 처리 보조)

| | |
|---|---|
| 메서드 | `GET` |
| 경로 | `/api/v1/predictions/jobs/{job_id}` |
| 권한 | `staff`, `admin` |

**Response — 200 OK (처리 중)**

```json
{
  "status": "processing",
  "job_id": "9f2c1b7e...",
  "record_id": 5
}
```

`status` 는 `queued`, `processing`, `done`, `failed` 중 하나다.

**Response — 200 OK (완료)**

```json
{
  "status": "done",
  "job_id": "9f2c1b7e...",
  "record_id": 5,
  "result": {
    "id": 12,
    "record_id": 5,
    "is_pneumonia": true,
    "confidence": 0.9821,
    "heatmap_url": null,
    "ai_model": "pneumonia_ensemble_v1",
    "created_at": "2026-07-21T14:03:11"
  }
}
```

**Response — 200 OK (실패)**

```json
{
  "status": "failed",
  "job_id": "9f2c1b7e...",
  "record_id": 5,
  "error": "이미지를 읽을 수 없습니다."
}
```

**에러**

| 코드 | 조건 |
|---|---|
| 401 / 403 | 위와 동일 |
| 404 | 존재하지 않거나 만료된 작업 ID (TTL 1시간) |

**클라이언트 폴링 가이드**

- 간격: 1초
- 최대: 30회 (30초). 초과 시 실패로 처리하고 재시도 안내
- `done` 또는 `failed` 를 받으면 폴링 중단

<br>

---

### 6-3. 예측 결과 목록 조회

REQ-PRED-002

| | |
|---|---|
| 메서드 | `GET` |
| 경로 | `/api/v1/medical-records/{record_id}/predictions` |
| 권한 | `staff`, `admin` |

**Response — 200 OK**

```json
{
  "record_id": 5,
  "xray_image_url": "/media/xray/3f9a2c....png",
  "predictions": [
    {
      "id": 12,
      "is_pneumonia": true,
      "confidence": 0.9821,
      "heatmap_url": null,
      "created_at": "2026-07-21T14:03:11",
      "ai_model": "pneumonia_ensemble_v1"
    },
    {
      "id": 8,
      "is_pneumonia": true,
      "confidence": 0.9540,
      "heatmap_url": null,
      "created_at": "2026-07-20T09:12:44",
      "ai_model": "pneumonia_baseline_v0"
    }
  ]
}
```

요구사항이 "해당 환자의 흉부 X-Ray 사진과 예측결과를 목록으로" 확인하도록 하므로, 이미지 URL을 함께 반환한다. 목록은 `created_at` 내림차순(최신순)으로 정렬한다.

결과가 없으면 `predictions` 는 빈 배열이며, 404가 아니다.

**에러**

| 코드 | 조건 |
|---|---|
| 401 / 403 | 위와 동일 |
| 404 | 존재하지 않는 진료기록 |

---

## 7. 처리 흐름 상세

### 7-1. 예측 요청 (6-1)

```
1. 진료기록 존재 확인            → 없으면 404
2. X-ray 이미지 존재 확인        → 없으면 422
3. 기존 예측 결과 조회
     (record_id + ai_model)
     └ 있으면 → 200 + 결과 반환 (여기서 종료)
4. 진행 중 작업 확인 (lock)
     └ 있으면 → 202 + 기존 job_id 반환
5. job_id 생성 (uuid4)
6. Redis: job 상태 = queued, lock 설정
7. Redis: 큐에 작업 push
8. 202 + job_id 반환
```

### 7-2. Worker

```
1. 서버 시작 시 PneumoniaEnsemble 1회 로드 (약 609MB)
2. BLPOP 으로 작업 대기 (블로킹)
3. 작업 수신 → job 상태 = processing
4. 이미지 파일 경로 확인 (media 볼륨 공유)
5. predictor.predict(경로) 실행
6. 결과를 ai_analysis_results 에 INSERT
7. job 상태 = done, result_id 기록, lock 해제
   (예외 발생 시 status = failed, error 기록, lock 해제)
8. 2번으로 돌아감
```

Worker는 `predict()` 내부에 `threading.Lock` 이 걸려 있어 한 프로세스 안에서는 항상 순차 처리된다. 처리량을 늘리려면 Worker 프로세스를 늘린다.

```bash
docker compose up --scale worker=2
```

Worker를 늘리면 각자 모델을 따로 적재하므로 메모리를 프로세스 수만큼 사용한다. (609MB × N)

---

## 8. 컨테이너 구성

```yaml
services:
  fastapi:      # 기존
  mysql:        # 기존
  redis:        # 추가 — 큐 + 작업 상태
  worker:       # 추가 — 모델 추론 전담
```

### 볼륨

| 볼륨 | 공유 대상 | 이유 |
|---|---|---|
| `media_volume` | fastapi ↔ worker | Worker가 업로드된 X-ray 파일을 읽어야 한다 |
| 모델 디렉토리 | worker (bind mount) | 609MB를 이미지에 넣지 않기 위해 |

### 모델 파일과 Git

모델 파일은 총 약 609MB이고 ConvNeXt 체크포인트 하나가 111MB로 **GitHub 파일 제한(100MB)을 초과**한다.

- `.gitignore` 에 `worker/models/` 추가
- 팀원에게는 별도 경로로 공유하고, 컨테이너에는 볼륨으로 연결
- 원격 저장이 필요하면 Git LFS 또는 object storage 검토

---

## 9. 요구사항 대응표

| 요구사항 | 대응 |
|---|---|
| REQ-PRED-001 예측 실행 | 6-1 (요청) + 6-2 (상태 조회) |
| REQ-PRED-001 저장된 X-ray 사용 | 요청 본문 없이 `record_id` 로 서버가 조회 |
| REQ-PRED-001 캐싱 | `record_id + ai_model` 조회, 있으면 200 즉시 반환 |
| REQ-PRED-001 결과 데이터 | `is_pneumonia`, `confidence`, `heatmap_url` |
| REQ-PRED-002 결과 목록 | 6-3, X-ray URL 동봉, 최신순 |
| NFR-PRED-001 모델 기준 | Accuracy 충족 / **Recall 미측정 → 검증 필요** |
| NFR-PRED-002 3초 이내 | 비동기 설계로 모든 API가 즉시 응답 |

---

## 10. 구현 노트 (코드를 읽을 때 참고)

코드만 봐서는 의도가 드러나지 않는 판단들을 정리한다.

### 10-1. 큐 등록 순서 — 큐에 넣는 것이 마지막이다

```python
1. job 상태 기록   (Redis Hash)
2. 자물쇠 설정     (Redis String)
3. 큐에 push       (Redis List)   ← 마지막
```

큐에 먼저 넣으면 Worker가 **너무 빨리** 꺼내가서, 작업 상태를 조회했을 때 아직 1번이 만들어지지 않은 상황이 생길 수 있다. 준비를 모두 끝낸 뒤 마지막에 알린다.

### 10-2. 자물쇠(lock)로 연타를 막는다

```
pneumonia:lock:{record_id}  =  job_id   (TTL 10분)
```

이 키가 없으면 사용자가 버튼을 3번 누를 때 3~5초짜리 추론이 3번 돌고, Worker는 그동안 다른 환자 요청을 받지 못한다. 키가 있으면 새 작업을 만들지 않고 **기존 `job_id` 를 그대로 반환**한다.

**TTL을 반드시 건다.** 기한이 없으면 추론 중 Worker가 죽었을 때 해당 진료기록은 영원히 예측할 수 없게 된다. 10분이 지나면 자동으로 풀려 재시도가 가능해진다.

### 10-3. 결과는 DB에만, Redis에는 위치만

작업이 끝나면 Redis에는 `result_id` 만 남기고, 실제 결과는 DB에서 읽는다.

- Redis 데이터는 TTL로 사라지지만 예측 결과는 영구 보존해야 한다
- 같은 데이터를 두 곳에 두면 언젠가 값이 어긋난다 (단일 진실 공급원)

### 10-4. try 블록에 Redis 작업만 넣는다

DB 조회는 `try` 밖에 둔다. **Redis가 죽어도 캐시된 결과 조회는 정상 동작해야 하기 때문이다.** 이미 저장된 결과가 있으면 Redis를 건드리지 않고 200을 반환한다.

### 10-5. Worker는 동기 코드다

API 서버는 `async def` 인데 Worker는 평범한 `def` 를 쓰고 DB 드라이버도 `pymysql`(동기)을 쓴다.

비동기는 "기다리는 동안 다른 일을 하려고" 쓰는 것인데, Worker가 하는 일은 **CPU가 계속 계산하는 추론**이라 기다림이 없다. 비동기로 만들어도 이득이 없고 코드만 복잡해진다.

### 10-6. BLPOP 을 쓰는 이유

```python
redis.blpop(QUEUE_KEY, timeout=5)
```

일반 `LPOP` 은 큐가 비면 즉시 `None` 을 반환하므로 `sleep` 을 넣고 반복해야 한다(폴링). CPU를 낭비하고 반응도 느리다.

`BLPOP` 은 작업이 들어올 때까지 **CPU를 쓰지 않고 대기하다가 즉시 반응**한다. `timeout=5` 는 5초마다 깨어나기 위한 것으로, 완전히 막혀 있으면 `docker stop` 에 반응하지 못한다.

### 10-7. Worker는 모든 예외를 잡는다

```python
try:
    self.handle(task)
except Exception as error:
    ...
```

평소에는 나쁜 습관이지만 Worker는 예외다. 이미지 하나가 깨져서 프로세스가 죽으면 **큐에 쌓인 다른 환자 요청이 전부 멈춘다.**

대신 세 가지를 반드시 한다.

1. `traceback.print_exc()` — 원인을 로그에 남긴다 (숨기지 않는다)
2. `status = failed` — 프론트가 영원히 기다리지 않게 알린다
3. **자물쇠 해제** — 실패해도 풀어야 재시도가 가능하다

### 10-8. Worker가 raw SQL 을 쓰는 이유

Worker는 독립 컨테이너다. ORM 모델을 쓰려면 FastAPI 코드 전체를 Worker 이미지에 넣어야 하는데, 테이블 3개만 다루는 데 비해 과하다.

대신 **바인딩 파라미터**를 반드시 사용한다. 문자열을 이어 붙이면 SQL 인젝션에 뚫린다.

```python
text("... WHERE record_id = :record_id"), {"record_id": record_id}   # O
f"... WHERE record_id = {record_id}"                                 # X
```

### 10-9. confidence 는 Decimal 로 변환해 저장한다

```python
Decimal(str(round(float(result["confidence"]), 4)))
```

`float` 은 근사값이라 `0.9821` 이 실제로는 `0.98209999...` 일 수 있다. `Numeric(5,4)` 컬럼에 정확히 넣기 위해 `float → str → Decimal` 순서로 변환한다.

### 10-10. pool_pre_ping 이 필요한 이유

```python
create_engine(DATABASE_URL, pool_pre_ping=True)
```

Worker는 요청이 없으면 몇 시간씩 대기한다. 그동안 MySQL이 유휴 연결을 끊는데, 이 옵션이 없으면 **오랜만에 들어온 첫 요청이 항상 실패**한다.

### 10-11. 로그 즉시 출력

```python
print(..., flush=True)          # worker/main.py
CMD ["python", "-u", ...]       # worker/Dockerfile
```

파이썬은 출력을 모아뒀다 내보내므로, 이 설정이 없으면 `docker compose logs -f` 에서 모델 로딩이 진행 중인지 멈춘 건지 알 수 없다.

---

## 11. 팀원이 알아야 할 것

### 11-1. Redis 키 이름은 두 파일에 중복 정의되어 있다

| 파일 | 대상 |
|---|---|
| `app/core/redis_client.py` | API 서버 |
| `worker/config.py` | Worker |

```python
QUEUE_KEY       = "pneumonia:queue"
JOB_KEY_PREFIX  = "pneumonia:job:"
LOCK_KEY_PREFIX = "pneumonia:lock:"
```

<br>

두 컨테이너가 코드를 공유하지 않으므로 각자 갖고 있다. **한쪽만 고치면 에러 없이 조용히 망가진다.** (작업을 넣어도 Worker가 영원히 못 찾는다) 반드시 양쪽을 함께 수정한다.

### 11-2. 모델 파일은 Git에 없다

약 609MB이고 체크포인트 하나가 111MB로 GitHub 제한(100MB)을 넘어 `.gitignore` 로 제외했다.

```
worker/models/pneumonia_ensemble_v1/     ← 별도 공유 필요
```

이 폴더가 없으면 Worker 컨테이너가 시작 직후 죽는다. 팀 공유 드라이브에서 받아 같은 경로에 두면 된다.

### 11-3. 실행 순서

```bash
uv add redis                              # API 서버 의존성
docker compose up -d --build
docker compose exec fastapi alembic upgrade head
docker compose logs -f worker             # "모델 로딩 완료" 확인
```

Worker 첫 기동은 모델 로딩 때문에 시간이 걸린다. 로그에 `모델 로딩 완료` 가 뜨기 전에는 예측 요청이 큐에 쌓이기만 한다.

### 11-4. 프론트엔드 연동 요약

```javascript
// 1. 예측 요청
const res = await fetch(`/api/v1/medical-records/${recordId}/predictions`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${accessToken}` },
});

// 2. 200이면 결과가 바로 온다 (이미 예측한 진료기록)
if (res.status === 200) {
  const { result } = await res.json();
  render(result);
  return;
}

// 3. 202면 job_id 로 1초마다 폴링 (최대 30회)
const { job_id } = await res.json();
// GET /api/v1/predictions/jobs/{job_id}
//   status: queued | processing → 계속 폴링
//   status: done                → result 렌더링
//   status: failed              → error 표시
```

---

## 12. 남은 과제

1. **Recall 측정** — NFR-PRED-001의 핵심 지표이며 아직 값이 없다.
2. **Heatmap** — 현재 모델은 생성하지 않는다. 필요하면 Grad-CAM을 별도 구현해야 한다.
3. **경량 profile** — 지금은 비동기로 우회했지만, 동기 응답이 필요해지면 fold 축소 후 정확도 재검증이 필요하다.
4. **Worker 장애 처리** — 추론 중 Worker가 죽으면 작업이 `processing` 상태로 남는다. 현재는 TTL(1시간) 만료에 의존한다.
