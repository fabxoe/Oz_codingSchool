# 3일차: DB 모델링 및 마이그레이션 작업 내용

## 1. 개요
- **목적:** 데이터 모델링 설계도와 현재 구현된 프로젝트의 DB 구조를 1:1로 일치시키기 위한 모델 수정 및 마이그레이션.
- **주요 수정 사항:**
    - AI 분석 결과 모델의 관계 재설정.
    - 의료진(User)과 엑스레이 업로드 행위의 관계 설정.
    - 불필요한 필드(MedicalRecord의 doctor_id) 제거를 통한 구조 최적화.

## 2. 변경 상세 내역
| 테이블(모델) | 수정 사항 | 이유 |
| :--- | :--- | :--- |
| **`AIAnalysisResult`** | `xray_image_id` 제거 | 설계도와 관계 일치 및 종속성 해소 |
| **`MedicalRecord`** | `doctor_id` 필드 제거 | 참고 설계도 구조와 동일하게 맞춤 |
| **`XRayImage`** | `uploader_id` 추가 | 사진 업로더 추적성 확보 (User 관계 연결) |
| **`User`** | `uploaded_xrays` 관계 추가 | 사진 업로드 기록 조회 가능하도록 설정 |

## 3. 마이그레이션 실행 결과
- 변경된 모델을 기반으로 `alembic` 자동 생성 기능을 통해 마이그레이션 스크립트 생성 및 적용 완료.
- **실행 명령어:**
```bash
uv run alembic revision --autogenerate -m "Align schema with reference diagram"
uv run alembic upgrade head