from pydantic import BaseModel, EmailStr
from enum import Enum


class UserRole(str, Enum):
    analyst = "analyst"
    manager = "manager"
    admin = "admin"


# Дані для реєстрації
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole = UserRole.analyst


# Дані для логіну
class UserLogin(BaseModel):
    username: str
    password: str


# Що повертаємо після логіну
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


# Що повертаємо про користувача
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str

    class Config:
        from_attributes = True


# Зміна ролі (тільки адмін)
class RoleUpdate(BaseModel):
    role: UserRole