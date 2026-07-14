from fastapi import APIRouter, Path
from fastapi import HTTPException

router = APIRouter()

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


def delete_user_handler():
    pass