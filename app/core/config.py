from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str = "ai_health"

    # JWT 설정 추가
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Redis 설정 (폐렴 예측 작업 큐)
    # 도커 네트워크 안에서는 서비스 이름 "redis" 로 접속한다.
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
