from fastapi import APIRouter, FastAPI, HTTPException, Path, status

app = FastAPI()

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


def get_users_handler():
    pass


def get_user_handler():
    pass


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