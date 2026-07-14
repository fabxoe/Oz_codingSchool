
from pydantic import BaseModel
from typing import List
from fastapi import APIRouter, FastAPI, HTTPException, Path, status


router = APIRouter()

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
# 모든 회원 목록 조회 API (요구사항 데코레이터와 응답 모델 적용)
@app.get("/practice_api/users", response_model=List[UserResponse])
def get_users_handler():
    # 이렇게 user_list를 바로 리턴해도, FastAPI가 UserResponse 모델에 맞춰 
    # password(비밀번호)를 자동으로 제외하고 필터링해 줍니다!
    return user_list


#현승
@router.get('/practice_api/users/{user_id}')
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


def create_user_handler():
    pass


def update_user_handler():
    pass


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