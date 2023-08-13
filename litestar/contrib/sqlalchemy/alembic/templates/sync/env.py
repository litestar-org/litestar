from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy import engine_from_config, pool

from litestar.contrib.sqlalchemy.base import orm_registry

__all__ = ["do_run_migrations", "run_migrations_offline", "run_migrations_online"]


if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from litestar.contrib.sqlalchemy.alembic.commands import AlembicCommandConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config: AlembicCommandConfig = context.config  # type: ignore


# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = orm_registry.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# ... etc.


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
        url=config.db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=config.compare_type,
        version_table=config.version_table_name,
        version_table_pk=config.version_table_pk,
        user_module_prefix=config.user_module_prefix,
        render_as_batch=config.render_as_batch,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=config.compare_type,
        version_table=config.version_table_name,
        version_table_pk=config.version_table_pk,
        user_module_prefix=config.user_module_prefix,
        render_as_batch=config.render_as_batch,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = config.db_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection=connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
