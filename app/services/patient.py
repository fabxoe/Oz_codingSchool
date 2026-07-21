from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.patient import Patient, Gender
from app.repositories.patient import PatientRepository
from app.schemas.patient import PatientCreate, PatientUpdate

class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.patient_repo = PatientRepository()

    async def create_patient(self, payload: PatientCreate) -> Patient:
        """환자 등록 서비스"""
        patient = Patient(
            name=payload.name,
            age=payload.age,
            gender=payload.gender,
            phone=payload.phone_number,
        )
        return await self.patient_repo.create(self.db, patient)

    async def get_patient_list(
        self,
        name: str | None = None,
        gender: Gender | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[Patient]:
        """환자 목록 조회 및 필터링 서비스"""
        return await self.patient_repo.get_list(
            self.db, name=name, gender=gender, min_age=min_age, max_age=max_age
        )

    async def get_patient_detail(self, patient_id: int) -> Patient:
        """환자 상세 조회 서비스 (없으면 404 에러 발생)"""
        patient = await self.patient_repo.get_by_id(self.db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 환자를 찾을 수 없습니다."
            )
        return patient

    async def update_patient(self, patient_id: int, payload: PatientUpdate) -> Patient:
        """환자 정보 수정 서비스"""
        patient = await self.get_patient_detail(patient_id)
        
        # 수정할 필드만 딕셔너리로 추출 (전송되지 않은 필드 제외)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 데이터가 없습니다."
            )

        # 모델 객체 속성 업데이트
        if "name" in update_data:
            patient.name = update_data["name"]
        if "phone_number" in update_data:
            patient.phone = update_data["phone_number"]

        return await self.patient_repo.update(self.db, patient)

    async def delete_patient(self, patient_id: int) -> None:
        """환자 삭제 서비스 (CASCADE 적용)"""
        patient = await self.get_patient_detail(patient_id)
        await self.patient_repo.delete(self.db, patient)