"""Worker 설정.

API 서버(app/core/config.py)와 별도로 둔다.
Worker 컨테이너에는 FastAPI 코드가 없으므로 pydantic-settings 대신
표준 라이브러리만 사용해 의존성을 최소화한다.
"""

import os

# --- DB ---
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password1234")
DB_HOST = os.getenv("DB_HOST", "mysql")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "ai_health")

# Worker는 비동기가 필요 없으므로 동기 드라이버(pymysql)를 쓴다.
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# --- Redis ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

QUEUE_KEY = "pneumonia:queue"
JOB_KEY_PREFIX = "pneumonia:job:"
LOCK_KEY_PREFIX = "pneumonia:lock:"

JOB_TTL_SECONDS = 60 * 60  # 1시간

# --- 파일 ---
# 업로드된 X-ray 이미지가 저장된 위치.
# DB에는 "/media/xray/<uuid>.png" 형태의 URL이 저장되어 있고,
# 실제 파일은 MEDIA_ROOT 아래에 있다.
MEDIA_ROOT = os.getenv("MEDIA_ROOT", "/app/media")

# --- 모델 ---
AI_MODEL_NAME = "pneumonia_ensemble_v1"
