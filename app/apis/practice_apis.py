

import re

from pydantic import BaseModel, Field, field_validator
from typing import List
from fastapi import APIRouter, FastAPI, HTTPException, Path, status

router = APIRouter(prefix="/practice_api", tags=["practice"])

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

# 강사님이 알려주신 응답 전용 데이터 모델 정의 (password 제외)
class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str
    # password 없음 → 응답에서 자동 제외
class UserBase(BaseModel):
    age: int | None = Field(None, ge=14)
    email: str | None = Field(None, max_length=30)
    password: str | None = Field(None, min_length=8, max_length=20)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not EMAIL_PATTERN.match(v):
            raise ValueError("올바른 이메일 형식이 아닙니다.")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.search(r"[A-Z]", v):
            raise ValueError("비밀번호에 대문자가 1개 이상 필요합니다.")
        if not re.search(r"[a-z]", v):
            raise ValueError("비밀번호에 소문자가 1개 이상 필요합니다.")
        if not SPECIAL_PATTERN.search(v):
            raise ValueError("비밀번호에 특수문자가 1개 이상 필요합니다.")
        return v 
class UserCreate(UserBase):
    name: str = Field(..., min_length=2, max_length=10)
    age: int = Field(..., ge=14)
    email: str = Field(..., max_length=30)
    password: str = Field(..., min_length=8, max_length=20)
class UserUpdate(UserBase):
    pass

# 모든 회원 목록 조회 API (요구사항 데코레이터와 응답 모델 적용)
@router.get("/users", response_model=List[UserResponse])
def get_users_handler():
    # 이렇게 user_list를 바로 리턴해도, FastAPI가 UserResponse 모델에 맞춰 
    # password(비밀번호)를 자동으로 제외하고 필터링해 줍니다!
    return user_list


#현승
@router.get('/users/{user_id}')
def get_user_handler(
    user_id:int = Path(..., ge=1)
):
    for user in user_list:
        if user['id'] == user_id:
            return {
                "id": user["id"],
                "name": user["name"],
                "age": user["age"],
                "email": user["email"]
            }
        

    raise HTTPException(
        status_code=404,
        detail="User not found"
        )


# 회원의 정보를 Request Body로 입력받아 user_list에 추가하는 API
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
SPECIAL_PATTERN = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]/\\~`';]")

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

    
@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user_handler(payload: UserUpdate, user_id: int):
    update_data = payload.model_dump(exclude_none=True)
    
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="수정할 항목을 최소 1개 이상 입력해야 합니다."
        )

    for user in user_list:
        if user["id"] == user_id:
            user.update(update_data)
            return user

    raise HTTPException(
        status_code=404,
        detail="User not found",
    )


# 회원의 id 값을 path parameter로 입력받아 특정 회원의 정보를 삭제하는 API
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_handler(user_id: int = Path(..., description="삭제할 회원의 id")):
    target_user = next((u for u in user_list if u["id"] == user_id), None)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"id가 {user_id}인 회원을 찾을 수 없습니다.",
        )

    user_list.remove(target_user)
    return None