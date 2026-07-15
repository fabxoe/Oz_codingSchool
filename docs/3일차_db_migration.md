# 3일차 - DB 모델 작성 및 마이그레이션

## 개요

ERD를 기반으로 SQLAlchemy ORM 모델을 작성하고, Alembic으로 마이그레이션을 생성하여 MySQL DB에 스키마를 적용한 과정을 정리한다.

- **DB**: MySQL 8.0 (Docker / Colima)
- **ORM**: SQLAlchemy 2.0 (async)
- **마이그레이션**: Alembic
- **뷰어**: DBeaver

---

## 1. 작성한 테이블

ERD 기준 5개 테이블 + Enum 3종을 작성했다.

| 테이블 | 설명 |
|---|---|
| `users` | 사내 구성원 (의료진/개발팀/연구진) |
| `patients` | 환자 정보 |
| `medical_records` | 진료 기록 |
| `xray_images` | X-ray 이미지 |
| `ai_analysis_results` | AI 폐렴 예측 결과 |

**Enum**: `Gender(M/F)`, `Role(PENDING/STAFF/ADMIN)`, `Department(MEDICAL/DEV/RESEARCH)`

**관계 (Foreign Key) 4개**

```
patients ──1:N──▶ medical_records ──1:N──▶ xray_images ──▶ users(uploader)
                        │
                        └──1:N──▶ ai_analysis_results
```

| FK | 참조 | ondelete |
|---|---|---|
| `medical_records.patient_id` | `patients.id` | CASCADE |
| `xray_images.record_id` | `medical_records.id` | CASCADE |
| `xray_images.uploader_id` | `users.id` | SET NULL |
| `ai_analysis_results.record_id` | `medical_records.id` | CASCADE |

---

## 2. 파일 구조

```
app/models/
├── __init__.py          # 모델 import 등록 (Alembic 감지용)
├── enums.py             # Gender, Role, Department
├── user.py              # User
├── patient.py           # Patient
├── medical_record.py    # MedicalRecord
├── xray_image.py        # XrayImage
└── ai_analysis_result.py # AIAnalysisResult
```

---

## 3. 마이그레이션 수행 과정

### 3-1. 모델 → Alembic 감지 흐름

```
alembic/env.py 의 from app import models
   → models/__init__.py 가 각 모델을 import
   → 각 모델이 Base 를 상속
   → Base.metadata 에 테이블 정보 등록
   → Alembic 이 target_metadata(=Base.metadata)를 보고 감지
```

### 3-2. revision 생성

```bash
uv run alembic revision --autogenerate -m "create initial tables"
```

`alembic/versions/` 하위에 마이그레이션 파일이 생성되었다. `upgrade()` 안에 `create_table` 5개와 `ForeignKeyConstraint` 4개, `downgrade()` 안에 `drop_table` 5개가 정상적으로 들어간 것을 확인했다.

### 3-3. DB 적용

```bash
uv run alembic upgrade head
```

```
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> cd5e40fd578e, create initial tables
```

---

## 4. DBeaver 확인

> 캡처 이미지는 Notion에 별도 업로드.

### 4-1. 테이블 목록

`ai_health` DB에 6개 테이블 생성 확인 (모델 5개 + `alembic_version`).

### 4-2. users 테이블 컬럼

컬럼 타입, PK, Not Null, Enum 확인. `gender`/`department`/`role` 이 Enum으로, `is_active` 가 `tinyint(1)` 로 생성되었다.

### 4-3. Foreign Key 확인

전체 ER 다이어그램(`Tables` 우클릭 → View Diagram)에서 FK 4개 관계가 ERD와 동일하게 연결된 것을 확인했다.

```
patients ──▶ medical_records ──▶ xray_images ──▶ users
                    │
                    └──▶ ai_analysis_results
```

---

## 5. 겪은 오류와 배운 점

### 오류 1: 모델 파일이 비어있어 ImportError 발생

모델 파일(`user.py` 등)을 만들기만 하고 클래스 내용을 채우지 않은 상태에서 마이그레이션을 시도했더니, `__init__.py` 가 빈 파일에서 `User` 를 import 하려다 실패했다.

```
ImportError: cannot import name 'User' from 'app.models.user'
```

에러 메시지가 `__init__.py` 몇 번째 줄에서 어떤 파일의 무엇을 못 찾았는지 정확히 알려주었다. 모델 클래스를 채운 뒤 정상 해결되었다.

### 배운 점: `alembic_version` 테이블

내가 만들지 않은 `alembic_version` 테이블이 자동 생성되었다. 이 테이블은 **현재 DB에 적용된 마이그레이션 버전(revision id)을 기록**하여, Alembic이 "어디까지 적용했는지"를 추적하는 용도다. 덕분에 `upgrade head` 를 여러 번 실행해도 중복 적용되지 않는다.

### 배운 점: FK 타입 일치

`xray_images.uploader_id` 는 `users.id` 를 참조하는데, `users.id` 가 `integer`(나머지 PK는 bigint)이므로 FK 컬럼 타입도 `Integer` 로 맞춰야 했다. 타입이 다르면 FK 생성 자체가 실패한다.

### 배운 점: MySQL의 boolean 저장 방식

`is_pneumonia`, `is_active` 같은 Boolean 컬럼이 DBeaver에서 `tinyint(1)` 로 표시되었다. MySQL은 boolean 타입이 없어 0/1의 tinyint로 저장하며, Python 코드에서는 다시 True/False로 읽힌다.
