# FastAPI 서버 이미지 (uv 기반)
#
# 이 프로젝트는 pyproject.toml + uv.lock 으로 의존성을 관리한다.
# 코드는 docker-compose 에서 볼륨(.:/code)으로 마운트하므로
# 여기서는 의존성 설치만 한다.

FROM python:3.13-slim

# curl: healthcheck 용
# build-essential: asyncmy(비동기 MySQL 드라이버)가 C 확장을 컴파일하는 데 필요
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# uv 설치 (공식 이미지에서 바이너리만 복사)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /code

# 의존성 목록만 먼저 복사 → 코드가 바뀌어도 설치 단계를 캐시에서 재사용
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 가상환경의 실행 파일을 PATH 에 추가 (uvicorn 등을 바로 실행)
ENV PATH="/code/.venv/bin:$PATH"

# 실제 코드와 실행 명령은 docker-compose 에서 주입한다.
