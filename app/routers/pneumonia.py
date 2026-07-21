from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, UploadFile, HTTPException
from worker.model import PneumoniaEnsemble

# 전역 predictor 변수 선언
predictor: PneumoniaEnsemble | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    # 앱 시작 시 모델을 메모리에 로드
    print("Loading pneumonia ensemble model...")
    predictor = PneumoniaEnsemble()
    yield
    # 앱 종료 시 메모리 해제
    predictor = None

router = APIRouter(prefix="/api/pneumonia", tags=["Pneumonia Prediction"])

@router.post("/predict")
async def predict_pneumonia(file: UploadFile):
    if predictor is None:
        raise HTTPException(status_code=500, detail="Prediction model is not loaded yet.")
    
    # 업로드된 파일 형식 검증 (이미지 파일 여부 확인)
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a chest X-ray image file.")

    try:
        # worker/model.py에 정의된 predict 메서드 호출
        result = predictor.predict(file.file)
        return {
            "filename": file.filename,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")