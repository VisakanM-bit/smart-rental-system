from __future__ import annotations

from passlib.context import CryptContext
from sqlalchemy import select
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_users(session) -> None:
    if session.scalar(select(User.id).limit(1)):
        return
    for username, password, role, name in [
        ("admin", "admin123", "admin", "System Administrator"),
        ("manager", "manager123", "manager", "Fleet Manager"),
        ("operator", "operator123", "operator", "Site Operator"),
        ("customer", "customer123", "customer", "Demo Customer"),
    ]:
        session.add(User(username=username, password_hash=pwd_context.hash(password), role=role, display_name=name))
    session.commit()


def authenticate(session, username: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.username == username.strip()))
    return user if user and pwd_context.verify(password, user.password_hash) else None
