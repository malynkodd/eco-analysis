"""Auth service — JWT issuer (RS256) and gateway verification endpoint."""
import logging
import os
from typing import List

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import SessionLocal, get_db

log = logging.getLogger(__name__)


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _cors_origins() -> List[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="Auth Service",
    root_path="/api/v1/auth",
    docs_url=None if _is_production() else "/docs",
    redoc_url=None if _is_production() else "/redoc",
    openapi_url=None if _is_production() else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.on_event("startup")
def bootstrap_admin() -> None:
    """Create the admin user from env vars on first boot.

    If an admin already exists, env vars are not required.
    If no admin exists and env vars are missing, startup fails fast.
    """
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth-service"}


# ─── Public endpoints ────────────────────────────────────────────────────────

@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    """Register a new user. Role is forced to `analyst`; clients cannot pick."""
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


@app.post("/login", response_model=schemas.TokenResponse)
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


@app.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ─── Admin endpoints ─────────────────────────────────────────────────────────

@app.get("/users", response_model=List[schemas.UserResponse])
def list_users(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return db.query(models.User).all()


@app.patch("/users/{user_id}/role", response_model=schemas.UserResponse)
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


# ─── Internal endpoint for the API gateway (NGINX auth_request) ──────────────

@app.get("/internal/verify", include_in_schema=False)
def internal_verify(
    response: Response,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Validate a Bearer token. Used by NGINX `auth_request`.

    On success: 204 + headers `X-User-Id`, `X-User-Username`, `X-User-Role`.
    On failure: 401.
    """
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
