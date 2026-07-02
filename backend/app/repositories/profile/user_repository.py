from sqlalchemy import select

from app.extensions.db import db
from app.models.user import User


def get_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def get_by_email(email: str) -> User | None:
    return db.session.scalar(select(User).where(User.email == email))


def get_by_username(username: str) -> User | None:
    return db.session.scalar(select(User).where(User.username == username))


def create(username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()
    return user


def update_avatar_url(user_id: int, avatar_url: str) -> User | None:
    user = db.session.get(User, user_id)
    if not user:
        return None
    user.avatar_url = avatar_url
    db.session.commit()
    return user


def update_profile(user_id: int, *, bio: str | None = None) -> User | None:
    user = db.session.get(User, user_id)
    if not user:
        return None
    if bio is not None:
        user.bio = bio
    db.session.commit()
    return user
