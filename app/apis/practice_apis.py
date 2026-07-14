import re

from fastapi import FastAPI, Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/practice_api", tags=["practice"])

app = FastAPI()

user_list = [
	{
		"id": 1,
		"name": "홍길동",
		"age": 24,
		"email": "gildong24@example.com",
		"password": "Password1234!!"
	},
	{
		"id": 2,
		"name": "장문복",
		"age": 21,
		"email": "moonluck12@example.com",
		"password": "Check1321!"
	},
	{
		"id": 3,
		"name": "임우진",
		"age": 31,
		"email": "limousine33@example.com",
		"password": "lwsPAssword12@"
	}
]


def get_users_handler():
    pass


def get_user_handler():
    pass


# 회원의 정보를 Request Body로 입력받아 user_list에 추가하는 API
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
SPECIAL_PATTERN = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]/\\~`';]")


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=10)
    age: int = Field(..., ge=14)
    email: str = Field(..., max_length=30)
    password: str = Field(..., min_length=8, max_length=20)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        if not EMAIL_PATTERN.match(v):
            raise ValueError("올바른 이메일 형식이 아닙니다.")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("비밀번호에 대문자가 1개 이상 필요합니다.")
        if not re.search(r"[a-z]", v):
            raise ValueError("비밀번호에 소문자가 1개 이상 필요합니다.")
        if not SPECIAL_PATTERN.search(v):
            raise ValueError("비밀번호에 특수문자가 1개 이상 필요합니다.")
        return v


class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str
    # password 없음 → 응답에서 자동 제외

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_handler(payload: UserCreate):
    # 이메일 중복 — user_list를 봐야 하므로 스키마가 아닌 여기서
    if any(u["email"] == payload.email for u in user_list):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다.",
        )

    new_id = max((u["id"] for u in user_list), default=0) + 1
    new_user = {"id": new_id, **payload.model_dump()}
    user_list.append(new_user)
    return new_user


def update_user_handler():
    pass


def delete_user_handler():
    pass