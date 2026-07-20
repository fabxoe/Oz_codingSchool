from pydantic import BaseModel, EmailStr

from app.models.user import Department, Gender, Role


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone_number: str
    gender: Gender
    department: Department


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    phone_number: str
    gender: Gender
    department: Department
    role: Role
    is_active: bool

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


class UserRoleUpdateRequest(BaseModel):
    user_id: int
    new_role: Role


class UserUpdateRequest(BaseModel):
    department: Department | None = None
    phone_number: str | None = None


class UserPasswordUpdateRequest(BaseModel):
    current_password: str
    new_password: str
