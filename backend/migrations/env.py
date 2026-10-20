"""Alembic environment: the database from Settings, the tables from the models.

Run from backend/:

    alembic -c migrations/alembic.ini upgrade head
"""

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.core.config import get_settings
from app.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

target_metadata = Base.metadata
# What Flask-Migrate passed before: column types count as a change, and
# migrations render ALTERs as batch operations (SQLite needed them; existing
# revisions use them).
CONFIGURE_ARGS = {"compare_type": True, "render_as_batch": True}


def _database_url() -> str:
    # A URL set on the config (alembic -x, or a test) wins over Settings.
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(), target_metadata=target_metadata, literal_binds=True, **CONFIGURE_ARGS
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    def skip_empty_autogenerate(context, revision, directives):
        # Do not write an empty revision when the models match the database.
        if getattr(config.cmd_opts, "autogenerate", False) and directives[0].upgrade_ops.is_empty():
            directives[:] = []
            logger.info("No changes in schema detected.")

    engine = create_engine(_database_url())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                process_revision_directives=skip_empty_autogenerate,
                **CONFIGURE_ARGS,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
