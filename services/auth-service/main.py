from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from database import get_db, engine, Base
import models
import schemas
import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service", root_path="/api/auth")


@app.on_event("startup")
def ensure_default_admin():
    """Create default admin user if absent, or fix role if wrong."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            admin = models.User(
                email="admin@eco-analysis.com",
                username="admin",
                hashed_password=auth.hash_password("admin123"),
                role=models.UserRole.admin,
            )
            db.add(admin)
            db.commit()
            print("✅ Default admin created: admin / admin123")
        elif admin.role != models.UserRole.admin:
            admin.role = models.UserRole.admin
            db.commit()
            print("✅ Admin role fixed")
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}


@app.post("/register", response_model=schemas.UserResponse)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """Реєстрація нового користувача"""

    existing_email = db.query(models.User).filter(
        models.User.email == user_data.email
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувач з таким email вже існує"
        )

    existing_username = db.query(models.User).filter(
        models.User.username == user_data.username
    ).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувач з таким іменем вже існує"
        )

    new_user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=auth.hash_password(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login", response_model=schemas.TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Логін через форму — повертає JWT токен"""

    user = db.query(models.User).filter(
        models.User.username == form_data.username
    ).first()

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний логін або пароль"
        )

    token = auth.create_access_token(data={
        "sub": user.username,
        "role": user.role.value
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "username": user.username
    }


@app.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    """Повертає дані поточного користувача по токену"""
    return current_user


@app.get("/users", response_model=List[schemas.UserResponse])
def get_users(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Список всіх користувачів — тільки для адміна"""
    if current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ тільки для адміністратора"
        )
    return db.query(models.User).all()


@app.patch("/users/{user_id}/role", response_model=schemas.UserResponse)
def change_user_role(
    user_id: int,
    role_data: schemas.RoleUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Змінити роль користувача — тільки адмін"""
    if current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ тільки для адміністратора"
        )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Адмін не може змінити власну роль"
        )
    user.role = role_data.role
    db.commit()
    db.refresh(user)
    return user