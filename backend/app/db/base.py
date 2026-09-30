"""The declarative base every model inherits from.

Plain SQLAlchemy, no Flask: code outside a Flask request (FastAPI routes,
scripts, tests) can use the models with an ordinary Session. Flask-SQLAlchemy
builds its db.Model on top of it (see app/extensions/db.py) while both
frameworks run side by side.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
