"""The declarative base every model inherits from.

Plain SQLAlchemy: routes, scripts and tests use the models with an ordinary
Session, and Alembic reads the tables from Base.metadata.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
