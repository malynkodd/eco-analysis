"""JWT signing (RS256) and password hashing for auth-service.

Auth-service is the ONLY component that holds the private key. All other
services verify with the public key (see services/<svc>/auth.py).
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import models
from database import get_db
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def _read_pem(path_env: str) -> str:
    path = Path(_require_env(path_env))
    if not path.is_file():
        raise RuntimeError(f"Key file does not exist: {path} (from {path_env})")
    return path.read_text()


JWT_PRIVATE_KEY = _read_pem("JWT_PRIVATE_KEY_PATH")
JWT_PUBLIC_KEY = _read_pem("JWT_PUBLIC_KEY_PATH")
JWT_ALGORITHM = "RS256"
JWT_ISSUER = _require_env("JWT_ISSUER")
JWT_AUDIENCE = _require_env("JWT_AUDIENCE")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

_BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))
if _BCRYPT_ROUNDS < 10:
    raise RuntimeError("BCRYPT_ROUNDS must be >= 10 for production-grade hashing")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=_BCRYPT_ROUNDS)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(*, subject: str, role: str, user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "uid": user_id,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRE_MINUTES)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, JWT_PRIVATE_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        JWT_PUBLIC_KEY,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    username = payload.get("sub")
    if not username:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user
