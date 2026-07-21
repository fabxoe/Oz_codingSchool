# app/services/medical_record.py
import os
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.medical_record import MedicalRecord
from app.models.xray_image import XrayImage
from app.repositories.patient import PatientRepository

MEDIA_DIR = "media/xray"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

class MedicalRecordService:
    @staticmethod
    async def create_medical_record(
        db: AsyncSession,
        patient_id: int,
        chart_number: str,
        symptoms: str,
        xray_image: UploadFile
    ) -> MedicalRecord:
        # 1. 환자 존재 여부 확인 (없으면 404)
        patient = await PatientRepository.get_by_id(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다."
            )

        # 2. 차트 번호 중복 확인 (중복 시 409)
        existing_chart = await db.execute(
            select(MedicalRecord).where(MedicalRecord.chart_number == chart_number)
        )
        if existing_chart.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 존재하는 차트 번호입니다."
            )

        # 3. 이미지 파일 확장자 검증 (허용되지 않으면 400)
        ext = os.path.splitext(xray_image.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지원하지 않는 이미지 형식입니다. (.jpg, .jpeg, .png만 허용)"
            )

        # 4. 고유 파일명 생성 및 저장소(media/xray)에 저장
        os.makedirs(MEDIA_DIR, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(MEDIA_DIR, unique_filename)

        try:
            contents = await xray_image.read()
            with open(file_path, "wb") as f:
                f.write(contents)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="파일 저장 중 오류가 발생했습니다."
            )

        image_url = f"/media/xray/{unique_filename}"

        # 5. MedicalRecord 생성 및 flush로 ID 확보
        record = MedicalRecord(
            patient_id=patient_id,
            chart_number=chart_number,
            symptoms=symptoms
        )
        db.add(record)
        await db.flush()  # ID를 먼저 받아오기 위해 flush 사용

        # 6. XrayImage 생성 및 연결
        xray = XrayImage(
            record_id=record.id,
            image_url=image_url
        )
        db.add(xray)

        await db.commit()
        await db.refresh(record)
        return record