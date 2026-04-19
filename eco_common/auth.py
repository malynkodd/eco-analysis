"""RS256 JWT verification — single shared implementation for every service.

Loads ONLY the public key (private key lives exclusively in auth-service).
Validates signature, issuer, audience, and exp/nbf. Returns the decoded
identity as a dict so endpoints can use ``Depends(get_current_user)``
without coupling to a SQLAlchemy session.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def _read_pem(path_env: str) -> str:
    path = Path(_require_env(path_env))
    if not path.is_file():
        raise RuntimeError(f"Public key file does not exist: {path}")
    return path.read_text()


JWT_PUBLIC_KEY = _read_pem("JWT_PUBLIC_KEY_PATH")
JWT_ALGORITHM = "RS256"
JWT_ISSUER = _require_env("JWT_ISSUER")
JWT_AUDIENCE = _require_env("JWT_AUDIENCE")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        JWT_PUBLIC_KEY,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
    )


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
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
    role = payload.get("role")
    user_id = payload.get("uid")
    if not username or not role:
        raise credentials_exception
    return {
        "username": username,
        "role": role,
        "user_id": user_id,
        "token": token,
    }
