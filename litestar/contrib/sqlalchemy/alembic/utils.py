from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import command as migration_command
from alembic.config import Config as AlembicCommandConfig
from sqlalchemy import Engine, Table
from sqlalchemy.schema import DropTable

from litestar.contrib.sqlalchemy.base import orm_registry

if TYPE_CHECKING:
    from alembic.runtime.environment import ProcessRevisionDirectiveFn


async def upgrade(
    migration_config: str, migration_path: str, revision: str = "head", sql: bool = False, tag: str | None = None
) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.upgrade(config=alembic_cfg, revision=revision, tag=tag, sql=sql)


async def downgrade(
    migration_config: str, migration_path: str, revision: str = "head", sql: bool = False, tag: str | None = None
) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.downgrade(config=alembic_cfg, revision=revision, tag=tag, sql=sql)


async def check(migration_config: str, migration_path: str) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.check(config=alembic_cfg)


async def current(migration_config: str, migration_path: str, verbose: bool = False) -> None:
    """Show current database revision."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.current(alembic_cfg, verbose=verbose)


async def edit(migration_config: str, migration_path: str, revision: str) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.edit(config=alembic_cfg, rev=revision)


async def ensure_version(migration_config: str, migration_path: str, sql: bool = False) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.ensure_version(config=alembic_cfg, sql=sql)


async def heads(
    migration_config: str, migration_path: str, verbose: bool = False, resolve_dependencies: bool = False
) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.heads(config=alembic_cfg, verbose=verbose, resolve_dependencies=resolve_dependencies)  # type: ignore[no-untyped-call]


async def history(
    migration_config: str,
    migration_path: str,
    rev_range: str | None = None,
    verbose: bool = False,
    indicate_current: bool = False,
) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.history(
        config=alembic_cfg, rev_range=rev_range, verbose=verbose, indicate_current=indicate_current
    )


async def merge(
    migration_config: str,
    migration_path: str,
    revisions: str,
    message: str | None = None,
    branch_label: str | None = None,
    rev_id: str | None = None,
) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.merge(
        config=alembic_cfg, revisions=revisions, message=message, branch_label=branch_label, rev_id=rev_id
    )


async def revision(
    migration_config: str,
    migration_path: str,
    message: str | None = None,
    autogenerate: bool = False,
    sql: bool = False,
    head: str = "head",
    splice: bool = False,
    branch_label: str | None = None,
    version_path: str | None = None,
    rev_id: str | None = None,
    depends_on: str | None = None,
    process_revision_directives: ProcessRevisionDirectiveFn | None = None,
) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.revision(
        config=alembic_cfg,
        message=message,
        autogenerate=autogenerate,
        sql=sql,
        head=head,
        splice=splice,
        branch_label=branch_label,
        version_path=version_path,
        rev_id=rev_id,
        depends_on=depends_on,
        process_revision_directives=process_revision_directives,
    )


async def show(migration_config: str, migration_path: str, rev: str) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.show(config=alembic_cfg, rev=rev)  # type: ignore[no-untyped-call]


async def stamp(
    migration_config: str,
    migration_path: str,
    revision: str,
    sql: bool = False,
    tag: str | None[str] = None,
    purge: bool = False,
) -> None:
    """Create database DDL migrations."""
    alembic_cfg = AlembicCommandConfig(migration_config)
    alembic_cfg.set_main_option("script_location", migration_path)
    migration_command.stamp(config=alembic_cfg, revision=revision, sql=sql, tag=tag, purge=purge)


def drop_tables(engine: Engine, version_table_name: str) -> None:
    """Drop all tables from the database.

    This should probably be a DB metadata inspection or a data dictionary query.

    This will not delete tables that don't currently exist within the SQLAlchemy metadata registry.
    """
    with engine.begin() as db:
        orm_registry.metadata.drop_all(db)
        db.execute(
            DropTable(
                element=Table(version_table_name, orm_registry.metadata),
                if_exists=True,
            ),
        )
        db.commit()
