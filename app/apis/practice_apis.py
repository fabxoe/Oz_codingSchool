from fastapi import FastAPI, Path
from pydantic import BaseModel  # pydantic 추가
from typing import List

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

# 강사님이 알려주신 응답 전용 데이터 모델 정의 (password 제외)
class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str
# 모든 회원 목록 조회 API (요구사항 데코레이터와 응답 모델 적용)
@app.get("/practice_api/users", response_model=List[UserResponse])
def get_users_handler():
    # 이렇게 user_list를 바로 리턴해도, FastAPI가 UserResponse 모델에 맞춰 
    # password(비밀번호)를 자동으로 제외하고 필터링해 줍니다!
    return user_list


def get_user_handler():
    pass


def create_user_handler():
    pass


def update_user_handler():
    pass


def delete_user_handler():
    pass