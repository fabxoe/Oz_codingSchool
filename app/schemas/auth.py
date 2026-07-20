from pydantic import BaseModel, EmailStr

# 회원가입 시 받을 데이터(1번 요청)
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

# 응답용 스키마 (hashed_password 제외!)(1번 요청)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    is_active: bool
    role: str

    class Config:
        from_attributes = True