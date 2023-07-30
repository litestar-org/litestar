from __future__ import annotations

from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from alembic.ddl.impl import DefaultImpl
from sqlalchemy import engine_from_config, pool

from litestar.contrib.sqlalchemy.base import orm_registry

__all__ = ["do_run_migrations", "run_migrations_offline", "run_migrations_online"]


if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

config = context.config
fileConfig(config.config_file_name)  # type: ignore
target_metadata = orm_registry.metadata


class SpannerImpl(DefaultImpl):
    __dialect__ = "spanner+spanner"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=settings.db.URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_pk=False,
        version_table=settings.db.MIGRATION_DDL_VERSION_TABLE,
        user_module_prefix="sa.",
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        version_table_pk=False,
        version_table=settings.db.MIGRATION_DDL_VERSION_TABLE,
        user_module_prefix="sa.",
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.db.URL
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
