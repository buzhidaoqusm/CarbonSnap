from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_for_update(session: Session, user_id: int) -> User | None:
    """Read the user and lock the row until the transaction ends.

    For read-check-write on the balance: a concurrent transaction asking for
    the same row waits for this one to commit, then reads the new value.
    populate_existing refreshes an object the session already holds, which
    would otherwise keep the value read before the lock.
    """
    return session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def get_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def create(session: Session, username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash)
    session.add(user)
    session.commit()
    return user


def update_avatar_url(session: Session, user_id: int, avatar_url: str) -> User | None:
    user = session.get(User, user_id)
    if not user:
        return None
    user.avatar_url = avatar_url
    session.commit()
    return user


def update_profile(session: Session, user_id: int, *, bio: str | None = None) -> User | None:
    user = session.get(User, user_id)
    if not user:
        return None
    if bio is not None:
        user.bio = bio
    session.commit()
    return user
