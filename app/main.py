import os
from pathlib import Path

from fastapi import FastAPI
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from app.apis.admin_api import router as admin_router
from app.apis.auth import router as session_router
from app.apis.auth_api import router as auth_router

app = FastAPI()

# Router 등록
app.include_router(auth_router)
app.include_router(session_router, prefix="/api/v1")
app.include_router(admin_router)

BASE_DIR = Path(__file__).resolve().parent.parent

# 만약 static, media 폴더가 존재하지 않으면 생성
if not (BASE_DIR / "static").exists():
    os.mkdir(BASE_DIR / "static")

if not (BASE_DIR / "media").exists():
    os.mkdir(BASE_DIR / "media")

# 정적 파일 마운트
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

app.mount(
    "/media",
    StaticFiles(directory=BASE_DIR / "media"),
    name="media",
)


@app.get(
    "/healthcheck",
    status_code=200,
    include_in_schema=False,
)
async def healthcheck():
    return {"status": "ok"}


@app.get(
    "/",
    include_in_schema=False,
)
async def index():
    return FileResponse(
        BASE_DIR / "static" / "index.html"
    )


@app.get(
    "/{path:path}",
    include_in_schema=False,
)
async def catch_all(path: str):
    if (
        path.startswith("api/v1")
        or path.startswith("static/")
        or path.startswith("media/")
    ):
        from fastapi import HTTPException

        raise HTTPException(status_code=404)

    return FileResponse(
        BASE_DIR / "static" / "index.html"
    )
