"""환자·진료기록 업무 로직 계층."""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import Gender
from app.repositories.patient_repository import (
    MedicalRecordRepository,
    PatientRepository,
)
from app.schemas.patient import PatientCreate, PatientUpdate

# 이미지 저장 위치
BASE_DIR = Path(__file__).resolve().parent.parent.parent
XRAY_DIR = BASE_DIR / "media" / "xray"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class PatientService:

    @staticmethod
    async def create(
        db: AsyncSession,
        payload: PatientCreate,
    ) -> Patient:
        """[REQ-PTNT-001] 환자 등록.

        스키마의 phone_number 를 ORM 속성 phone 으로 변환한다.
        """
        patient = Patient(
            name=payload.name,
            age=payload.age,
            gender=payload.gender,
            phone=payload.phone_number,  # 이름이 다름!
        )
        return await PatientRepository.create(db, patient)

    @staticmethod
    async def get_list(
        db: AsyncSession,
        name: str | None = None,
        gender: Gender | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[Patient]:
        """[REQ-PTNT-002] 환자 목록 조회 (검색·필터)."""
        return await PatientRepository.get_all(
            db,
            name=name,
            gender=gender,
            min_age=min_age,
            max_age=max_age,
        )

    @staticmethod
    async def get_detail(
        db: AsyncSession,
        patient_id: int,
    ) -> Patient:
        """[REQ-PTNT-003] 환자 상세 조회."""
        patient = await PatientRepository.get_by_id(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 환자입니다.",
            )
        return patient

    @staticmethod
    async def update(
        db: AsyncSession,
        patient_id: int,
        payload: PatientUpdate,
    ) -> Patient:
        """[REQ-PTNT-004] 환자 정보 수정 (이름, 연락처).

        exclude_unset=True 가 핵심이다. 이걸 빼면 전달하지 않은 필드까지
        None 으로 덮어써서 데이터가 소실된다.
        """
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 항목이 없습니다.",
            )

        patient = await PatientService.get_detail(db, patient_id)

        if "name" in update_data:
            patient.name = update_data["name"]
        if "phone_number" in update_data:
            patient.phone = update_data["phone_number"]  # 변환

        return await PatientRepository.update(db, patient)

    @staticmethod
    async def delete(
        db: AsyncSession,
        patient_id: int,
    ) -> None:
        """[REQ-PTNT-005] 환자 삭제 (진료기록·X-ray도 CASCADE 삭제)."""
        patient = await PatientService.get_detail(db, patient_id)
        await PatientRepository.delete(db, patient)


class MedicalRecordService:

    @staticmethod
    def _save_image(xray_image: UploadFile) -> str:
        """이미지를 로컬에 저장하고 응답용 URL을 반환한다.

        실제 파일: 프로젝트/media/xray/<uuid>.jpg
        응답 URL : /media/xray/<uuid>.jpg

        업로드된 파일명을 그대로 쓰면 같은 이름의 파일이 덮어써지므로
        서버에서 고유한 이름을 만든다.
        """
        extension = Path(xray_image.filename or "").suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="jpg, jpeg, png 형식만 업로드할 수 있습니다.",
            )

        XRAY_DIR.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{extension}"
        file_path = XRAY_DIR / filename

        with open(file_path, "wb") as buffer:
            buffer.write(xray_image.file.read())

        return f"/media/xray/{filename}"

    @staticmethod
    async def create(
        db: AsyncSession,
        patient_id: int,
        chart_number: str,
        symptoms: str,
        xray_image: UploadFile,
        uploader_id: int,
        shooting_datetime: datetime | None = None,
    ) -> MedicalRecord:
        """[REQ-MDR-001] 진료기록 등록 (X-ray 이미지 포함).

        순서: 환자 존재 확인 → 차트번호 중복 확인 → 이미지 검증·저장
              → MedicalRecord 추가 → flush(id 확보) → XrayImage 추가 → commit

        DB 검증을 파일 저장보다 먼저 한다. 그래야 검증 실패 시
        저장된 파일만 남는 상황을 피할 수 있다.
        """
        # 1. 환자 존재 확인
        patient = await PatientRepository.get_by_id(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 환자입니다.",
            )

        # 2. 차트번호 중복 확인
        existing = await MedicalRecordRepository.get_by_chart_number(
            db, chart_number
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 차트 번호입니다.",
            )

        # 3. 이미지 검증 및 저장
        image_url = MedicalRecordService._save_image(xray_image)

        # 4. 진료기록 + X-ray 저장
        record = MedicalRecord(
            patient_id=patient_id,
            chart_number=chart_number,
            symptoms=symptoms,
        )
        return await MedicalRecordRepository.create_with_image(
            db,
            record=record,
            image_url=image_url,
            uploader_id=uploader_id,
            shooting_datetime=shooting_datetime or datetime.now(),
        )

    @staticmethod
    async def get_list_by_patient(
        db: AsyncSession,
        patient_id: int,
    ) -> list[MedicalRecord]:
        """[REQ-MDR-002] 환자별 진료기록 목록."""
        await PatientService.get_detail(db, patient_id)  # 404 검사
        return await MedicalRecordRepository.get_all_by_patient(db, patient_id)

    @staticmethod
    async def get_detail(
        db: AsyncSession,
        record_id: int,
    ) -> dict:
        """[REQ-MDR-003] 진료기록 상세 (X-ray 이미지 URL 포함)."""
        record = await MedicalRecordRepository.get_by_id(db, record_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 진료기록입니다.",
            )

        # 스키마의 xray_image_url 은 ORM에 없는 필드이므로 직접 조립한다.
        xray_image_url = (
            record.xray_images[0].image_url if record.xray_images else None
        )

        return {
            "id": record.id,
            "patient_id": record.patient_id,
            "chart_number": record.chart_number,
            "symptoms": record.symptoms,
            "xray_image_url": xray_image_url,
            "created_at": record.created_at,
        }
