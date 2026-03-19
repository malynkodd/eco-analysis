from sqlalchemy import Column, Integer, String, Enum
from database import Base
import enum


# Три ролі як зазначено в ТЗ
class UserRole(str, enum.Enum):
    analyst = "analyst"      # аналітик — створює проєкти, запускає аналіз
    manager = "manager"      # менеджер — переглядає звіти, затверджує рішення
    admin = "admin"          # адміністратор — управляє користувачами


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.analyst, nullable=False)