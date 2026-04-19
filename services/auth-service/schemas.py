from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    analyst = "analyst"
    manager = "manager"
    admin = "admin"


class UserRegister(BaseModel):
    """Public registration. The role is fixed to 'analyst' server-side; any
    client-supplied role field is rejected."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _username_no_spaces(cls, v: str) -> str:
        if any(c.isspace() for c in v):
            raise ValueError("username must not contain whitespace")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    """Admin-only role change."""

    role: UserRole


class VerifyResponse(BaseModel):
    """Returned by the gateway-internal token verification endpoint."""

    valid: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
