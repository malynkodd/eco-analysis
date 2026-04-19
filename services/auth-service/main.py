"""Auth service — JWT issuer (RS256) and gateway verification endpoint."""
from __future__ import annotations

import logging
import os
from typing import List

from fastapi import Depends, Header, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import SessionLocal, get_db
from eco_common.api_setup import create_app
from eco_common.envelope import paginate

log = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "auth", "description": "Login, registration, current user."},
    {"name": "users", "description": "Admin-only user management."},
    {"name": "internal", "description": "Gateway-only verification endpoint."},
    {"name": "system", "description": "Health and metadata."},
]

app = create_app(
    title="Auth Service",
    description="JWT issuance, user registry, gateway verification.",
    root_path="/api/v1/auth",
    openapi_tags=OPENAPI_TAGS,
)


@app.on_event("startup")
def bootstrap_admin() -> None:
    db: Session = SessionLocal()
    try:
        existing_admin = (
            db.query(models.User).filter(models.User.role == models.UserRole.admin).first()
        )
        if existing_admin:
            log.info("Admin '%s' already present; skipping bootstrap.", existing_admin.username)
            return

        username = os.getenv("ADMIN_USERNAME")
        password = os.getenv("ADMIN_PASSWORD")
        email = os.getenv("ADMIN_EMAIL")
        if not username or not password or not email:
            raise RuntimeError(
                "No admin user exists and ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_EMAIL "
                "are not set. Cannot bootstrap admin."
            )
        if len(password) < 8:
            raise RuntimeError("ADMIN_PASSWORD must be at least 8 characters.")

        admin = models.User(
            email=email,
            username=username,
            hashed_password=auth.hash_password(password),
            role=models.UserRole.admin,
        )
        db.add(admin)
        db.commit()
        log.info("Admin user '%s' bootstrapped from env.", username)
    finally:
        db.close()


@app.get("/health", tags=["system"], summary="Liveness probe")
def health() -> dict:
    return {"status": "ok", "service": "auth-service"}


@app.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
    summary="Register a new analyst user",
)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = models.User(
        email=payload.email,
        username=payload.username,
        hashed_password=auth.hash_password(payload.password),
        role=models.UserRole.analyst,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post(
    "/login",
    response_model=schemas.TokenResponse,
    tags=["auth"],
    summary="Exchange username/password for an RS256 access token",
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid login or password")

    token = auth.create_access_token(
        subject=user.username, role=user.role.value, user_id=user.id
    )
    return schemas.TokenResponse(
        access_token=token, token_type="bearer", role=user.role.value, username=user.username
    )


@app.get(
    "/me",
    response_model=schemas.UserResponse,
    tags=["auth"],
    summary="Return the current user's profile",
)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@app.get(
    "/users",
    tags=["users"],
    summary="List all users (admin only)",
)
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    base = db.query(models.User).order_by(models.User.id.desc())
    total = base.count()
    rows = base.offset((page - 1) * limit).limit(limit).all()
    items = [schemas.UserResponse.model_validate(u, from_attributes=True) for u in rows]
    return paginate(items=items, page=page, limit=limit, total=total)


@app.patch(
    "/users/{user_id}/role",
    response_model=schemas.UserResponse,
    tags=["users"],
    summary="Promote or demote a user (admin only)",
)
def change_user_role(
    user_id: int,
    payload: schemas.RoleUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Admin cannot change their own role")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@app.get("/internal/verify", include_in_schema=False, tags=["internal"])
def internal_verify(
    response: Response,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(None, 1)[1].strip()
    try:
        payload = auth.decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first() if username else None
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    response.headers["X-User-Id"] = str(user.id)
    response.headers["X-User-Username"] = user.username
    response.headers["X-User-Role"] = user.role.value
    response.status_code = 204
    return None
