"""환자·진료기록 API.

[REQ-PTNT-001~005] 환자 등록·목록·상세·수정·삭제
[REQ-MDR-001~003]  진료기록 등록·목록·상세

권한 (5일차 설계 문서 기준):
  - 환자/진료기록 조회: 로그인한 사용자
  - 환자 등록, 진료기록 등록: staff 또는 admin
  - 환자 수정/삭제: 로그인한 사용자
"""

from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Path,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user, require_roles
from app.models.user import Gender, Role, User
from app.schemas.patient import (
    MedicalRecordDetailResponse,
    MedicalRecordListResponse,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import MedicalRecordService, PatientService

router = APIRouter(prefix="/api/v1", tags=["Patients"])

# 등록(환자·진료기록)에만 요구되는 권한.
# 수정·삭제는 설계 문서상 로그인한 사용자면 가능하다.
require_staff_or_admin = require_roles(Role.STAFF, Role.ADMIN)


def _to_response(patient) -> dict:
    """ORM의 phone → 응답의 phone_number 로 변환."""
    return {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "phone_number": patient.phone,
        "created_at": patient.created_at,
        "updated_at": patient.updated_at,
    }


# ============================================================
# 환자
# ============================================================


# [REQ-PTNT-001] 사내 의료인 역할을 가진 유저는 환자 정보를 등록할 수 있다.
@router.post(
    "/patients",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="환자 등록",
)
async def create_patient(
    payload: PatientCreate,
    current_user: User = Depends(require_staff_or_admin),
    db: AsyncSession = Depends(async_get_db),
):
    patient = await PatientService.create(db, payload)
    return _to_response(patient)


# [REQ-PTNT-002] 로그인된 사용자는 환자 목록을 조회할 수 있다. (검색·필터)
@router.get(
    "/patients",
    response_model=list[PatientResponse],
    status_code=status.HTTP_200_OK,
    summary="환자 목록 조회",
)
async def list_patients(
    name: str | None = Query(None, description="이름 부분 검색"),
    gender: Gender | None = Query(None, description="성별 필터"),
    min_age: int | None = Query(None, ge=0, description="최소 나이"),
    max_age: int | None = Query(None, ge=0, description="최대 나이"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    patients = await PatientService.get_list(
        db, name=name, gender=gender, min_age=min_age, max_age=max_age
    )
    return [_to_response(p) for p in patients]


# [REQ-PTNT-003] 환자 상세 정보를 조회할 수 있다.
@router.get(
    "/patients/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="환자 상세 조회",
)
async def get_patient(
    patient_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    patient = await PatientService.get_detail(db, patient_id)
    return _to_response(patient)


# [REQ-PTNT-004] 환자의 정보(이름, 연락처)를 수정할 수 있다.
@router.patch(
    "/patients/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="환자 정보 수정",
)
async def update_patient(
    payload: PatientUpdate,
    patient_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    patient = await PatientService.update(db, patient_id, payload)
    return _to_response(patient)


# [REQ-PTNT-005] 환자와 관련된 진료기록·X-ray 이미지도 함께 영구 삭제한다.
@router.delete(
    "/patients/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="환자 삭제",
)
async def delete_patient(
    patient_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    await PatientService.delete(db, patient_id)
    return None


# ============================================================
# 진료기록
# ============================================================


# [REQ-MDR-001] 사내 의료인은 X-Ray 사진을 포함한 진료기록을 등록할 수 있다.
@router.post(
    "/medical-records",
    response_model=MedicalRecordDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="진료기록 등록 (X-ray 이미지 포함)",
)
async def create_medical_record(
    # 파일이 포함되므로 JSON이 아닌 multipart/form-data 로 받는다.
    # Pydantic 모델과 UploadFile 을 한 요청에 섞을 수 없으므로
    # 모든 필드를 Form(...) 으로 선언한다.
    patient_id: int = Form(..., ge=1),
    chart_number: str = Form(..., max_length=50),
    symptoms: str = Form(...),
    xray_image: UploadFile = File(...),
    shooting_datetime: datetime | None = Form(None),
    current_user: User = Depends(require_staff_or_admin),
    db: AsyncSession = Depends(async_get_db),
):
    record = await MedicalRecordService.create(
        db,
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
        xray_image=xray_image,
        uploader_id=current_user.id,
        shooting_datetime=shooting_datetime,
    )
    return await MedicalRecordService.get_detail(db, record.id)


# [REQ-MDR-002] 특정 환자의 진료기록을 목록으로 확인할 수 있다.
@router.get(
    "/patients/{patient_id}/medical-records",
    response_model=list[MedicalRecordListResponse],
    status_code=status.HTTP_200_OK,
    summary="환자별 진료기록 목록",
)
async def list_medical_records(
    patient_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await MedicalRecordService.get_list_by_patient(db, patient_id)


# [REQ-MDR-003] 진료기록 상세 조회 (흉부 X-Ray 이미지 포함).
@router.get(
    "/medical-records/{record_id}",
    response_model=MedicalRecordDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="진료기록 상세 조회",
)
async def get_medical_record(
    record_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await MedicalRecordService.get_detail(db, record_id)
