from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from alembic import command as migration_command
from alembic.config import Config as _AlembicCommandConfig
from alembic.ddl.impl import DefaultImpl

if TYPE_CHECKING:
    from alembic.runtime.environment import ProcessRevisionDirectiveFn


class AlembicCommandConfig(_AlembicCommandConfig):
    def get_template_directory(self) -> str:
        """Return the directory where Alembic setup templates are found.

        This method is used by the alembic ``init`` and ``list_templates``
        commands.

        """
        from litestar.contrib.sqlalchemy import alembic

        package_dir = Path(alembic.__file__).parent.resolve()
        return str(Path(package_dir / "templates"))


class AlembicSpannerImpl(DefaultImpl):
    """Alembic implementation for Spanner."""

    __dialect__ = "spanner+spanner"


def get_alembic_config(
    migration_config: str | None = None, script_location: str = "migrations"
) -> AlembicCommandConfig:
    kwargs = {}
    if migration_config:
        kwargs["file_"] = migration_config
    alembic_cfg = AlembicCommandConfig(**kwargs)  # type: ignore
    alembic_cfg.set_main_option("script_location", script_location)
    return alembic_cfg


async def upgrade(
    migration_config: str | None = None,
    script_location: str = "migrations",
    revision: str = "head",
    sql: bool = False,
    tag: str | None = None,
) -> None:
    """Create or upgrade a database."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.upgrade(config=alembic_cfg, revision=revision, tag=tag, sql=sql)


async def downgrade(
    migration_config: str | None = None,
    script_location: str = "migrations",
    revision: str = "head",
    sql: bool = False,
    tag: str | None = None,
) -> None:
    """Downgrade a database to a specific revision."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.downgrade(config=alembic_cfg, revision=revision, tag=tag, sql=sql)


async def check(
    migration_config: str | None = None,
    script_location: str = "migrations",
) -> None:
    """Check if revision command with autogenerate has pending upgrade ops."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.check(config=alembic_cfg)


async def current(
    migration_config: str | None = None, script_location: str = "migrations", verbose: bool = False
) -> None:
    """Display the current revision for a database."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.current(alembic_cfg, verbose=verbose)


async def edit(
    revision: str,
    migration_config: str | None = None,
    script_location: str = "migrations",
) -> None:
    """Edit revision script(s) using $EDITOR."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.edit(config=alembic_cfg, rev=revision)


async def ensure_version(
    migration_config: str | None = None, script_location: str = "migrations", sql: bool = False
) -> None:
    """Create the alembic version table if it doesn't exist already."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.ensure_version(config=alembic_cfg, sql=sql)


async def heads(
    migration_config: str | None = None,
    script_location: str = "migrations",
    verbose: bool = False,
    resolve_dependencies: bool = False,
) -> None:
    """Show current available heads in the script directory."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.heads(config=alembic_cfg, verbose=verbose, resolve_dependencies=resolve_dependencies)  # type: ignore[no-untyped-call]


async def history(
    migration_config: str | None = None,
    script_location: str = "migrations",
    rev_range: str | None = None,
    verbose: bool = False,
    indicate_current: bool = False,
) -> None:
    """List changeset scripts in chronological order."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.history(
        config=alembic_cfg, rev_range=rev_range, verbose=verbose, indicate_current=indicate_current
    )


async def merge(
    revisions: str,
    migration_config: str | None = None,
    script_location: str = "migrations",
    message: str | None = None,
    branch_label: str | None = None,
    rev_id: str | None = None,
) -> None:
    """Merge two revisions together. Creates a new migration file."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.merge(
        config=alembic_cfg, revisions=revisions, message=message, branch_label=branch_label, rev_id=rev_id
    )


async def revision(
    migration_config: str | None = None,
    script_location: str = "migrations",
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
    """Create a new revision file."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
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


async def show(
    rev: Any,
    migration_config: str | None = None,
    script_location: str = "migrations",
) -> None:
    """Show the revision(s) denoted by the given symbol."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.show(config=alembic_cfg, rev=rev)  # type: ignore[no-untyped-call]


async def init(
    directory: str,
    migration_config: str | None = None,
    template_path: str | None = None,
    script_location: str = "migrations",
    template: str = "generic",
    package: bool = False,
) -> None:
    """Initialize a new scripts directory."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.init(config=alembic_cfg, directory=directory, template=template, package=package)


async def list_templates(migration_config: str | None, script_location: str = "migrations") -> None:
    """List available templates."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.list_templates(config=alembic_cfg)


async def stamp(
    migration_config: str,
    revision: str,
    script_location: str = "migrations",
    sql: bool = False,
    tag: str | None[str] = None,
    purge: bool = False,
) -> None:
    """'stamp' the revision table with the given revision; don't run any migrations."""
    alembic_cfg = get_alembic_config(migration_config=migration_config, script_location=script_location)
    migration_command.stamp(config=alembic_cfg, revision=revision, sql=sql, tag=tag, purge=purge)
