import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_record import MedicalRecord
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.medical_record import (
    MedicalRecordDetailResponse,
    MedicalRecordListItem,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
XRAY_DIR = BASE_DIR / "media" / "xray"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class MedicalRecordService:

    @staticmethod
    async def _save_image(xray_image: UploadFile) -> tuple[str, Path]:
        extension = Path(xray_image.filename or "").suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="jpg, jpeg, png 형식만 업로드할 수 있습니다.",
            )

        contents = await xray_image.read()
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="빈 이미지 파일은 업로드할 수 없습니다.",
            )

        XRAY_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{extension}"
        file_path = XRAY_DIR / filename

        try:
            file_path.write_bytes(contents)
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이미지 저장 중 오류가 발생했습니다.",
            ) from exc

        return f"/media/xray/{filename}", file_path

    @staticmethod
    async def create(
        db: AsyncSession,
        patient_id: int,
        chart_number: str,
        symptoms: str,
        xray_image: UploadFile,
        uploader_id: int,
    ) -> MedicalRecordDetailResponse:
        patient = await PatientRepository.get_by_id(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다.",
            )

        existing_record = await MedicalRecordRepository.get_by_chart_number(
            db,
            chart_number,
        )
        if existing_record is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 존재하는 차트 번호입니다.",
            )

        image_url, file_path = await MedicalRecordService._save_image(xray_image)
        record = MedicalRecord(
            patient_id=patient_id,
            chart_number=chart_number,
            symptoms=symptoms,
        )

        try:
            record = await MedicalRecordRepository.create_with_image(
                db,
                record=record,
                image_url=image_url,
                uploader_id=uploader_id,
                shooting_datetime=datetime.now(),
            )
        except Exception:
            await db.rollback()
            file_path.unlink(missing_ok=True)
            raise

        return MedicalRecordDetailResponse(
            id=record.id,
            patient_id=record.patient_id,
            chart_number=record.chart_number,
            symptoms=record.symptoms,
            xray_image_url=image_url,
            created_at=record.created_at,
        )

    @staticmethod
    async def get_records_by_patient(
        db: AsyncSession,
        patient_id: int,
    ) -> list[MedicalRecordListItem]:
        patient = await PatientRepository.get_by_id(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다.",
            )

        records = await MedicalRecordRepository.get_by_patient_id(db, patient_id)
        return [MedicalRecordListItem.model_validate(record) for record in records]

    @staticmethod
    async def get_record_detail(
        db: AsyncSession,
        record_id: int,
    ) -> MedicalRecordDetailResponse:
        record = await MedicalRecordRepository.get_by_id(db, record_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료기록을 찾을 수 없습니다.",
            )

        image_url = await MedicalRecordRepository.get_latest_xray_image_url(
            db,
            record_id,
        )
        return MedicalRecordDetailResponse(
            id=record.id,
            patient_id=record.patient_id,
            chart_number=record.chart_number,
            symptoms=record.symptoms,
            xray_image_url=image_url,
            created_at=record.created_at,
        )
