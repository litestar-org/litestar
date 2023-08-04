from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, TextIO

from alembic import command as migration_command
from alembic.config import Config as _AlembicCommandConfig
from alembic.ddl.impl import DefaultImpl

from litestar.contrib.sqlalchemy.plugins.init.config.asyncio import SQLAlchemyAsyncConfig
from litestar.contrib.sqlalchemy.plugins.init.plugin import SQLAlchemyInitPlugin

if TYPE_CHECKING:
    import os
    from argparse import Namespace

    from alembic.runtime.environment import ProcessRevisionDirectiveFn
    from sqlalchemy import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine

    from litestar.app import Litestar
    from litestar.contrib.sqlalchemy.plugins.init.config.sync import SQLAlchemySyncConfig


class AlembicCommandConfig(_AlembicCommandConfig):
    def __init__(
        self,
        file_: str | os.PathLike[str] | None = None,
        ini_section: str = "alembic",
        output_buffer: TextIO | None = None,
        stdout: TextIO = sys.stdout,
        cmd_opts: Namespace | None = None,
        config_args: Mapping[str, Any] | None = None,
        attributes: dict | None = None,
        template_directory: Path | None = None,
        version_table_name: str | None = None,
        db_url: str | None = None,
        engine: Engine | AsyncEngine | None = None,
    ) -> None:
        self.template_directory = template_directory
        self.version_table_name = version_table_name
        self.db_url = db_url
        self.engine = engine
        if config_args is None:
            config_args = {}
        super().__init__(file_, ini_section, output_buffer, stdout, cmd_opts, config_args, attributes)

    def get_template_directory(self) -> str:
        """Return the directory where Alembic setup templates are found.

        This method is used by the alembic ``init`` and ``list_templates``
        commands.

        """
        if self.template_directory is not None:
            return str(self.template_directory)
        return super().get_template_directory()


class AlembicSpannerImpl(DefaultImpl):
    """Alembic implementation for Spanner."""

    __dialect__ = "spanner+spanner"


def get_alembic_command_config(config: SQLAlchemyAsyncConfig | SQLAlchemySyncConfig) -> AlembicCommandConfig:
    kwargs = {}
    engine = config.create_engine()
    if config.alembic_config.script_config:
        kwargs["file_"] = config.alembic_config.script_config
    if config.alembic_config.template_path:
        kwargs["template_directory"] = config.alembic_config.template_path
    alembic_cfg = AlembicCommandConfig(**kwargs)  # type: ignore
    alembic_cfg.set_main_option("script_location", config.alembic_config.script_location)
    alembic_cfg.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False).replace("%", "%%"))
    return alembic_cfg


def upgrade(
    app: Litestar,
    revision: str = "head",
    sql: bool = False,
    tag: str | None = None,
) -> None:
    """Create or upgrade a database."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.upgrade(config=alembic_cfg, revision=revision, tag=tag, sql=sql)


def downgrade(
    app: Litestar,
    revision: str = "head",
    sql: bool = False,
    tag: str | None = None,
) -> None:
    """Downgrade a database to a specific revision."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.downgrade(config=alembic_cfg, revision=revision, tag=tag, sql=sql)


def check(
    app: Litestar,
) -> None:
    """Check if revision command with autogenerate has pending upgrade ops."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.check(config=alembic_cfg)


def current(app: Litestar, verbose: bool = False) -> None:
    """Display the current revision for a database."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.current(alembic_cfg, verbose=verbose)


def edit(app: Litestar, revision: str) -> None:
    """Edit revision script(s) using $EDITOR."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.edit(config=alembic_cfg, rev=revision)


def ensure_version(app: Litestar, sql: bool = False) -> None:
    """Create the alembic version table if it doesn't exist already."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.ensure_version(config=alembic_cfg, sql=sql)


def heads(app: Litestar, verbose: bool = False, resolve_dependencies: bool = False) -> None:
    """Show current available heads in the script directory."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.heads(config=alembic_cfg, verbose=verbose, resolve_dependencies=resolve_dependencies)  # type: ignore[no-untyped-call]


def history(
    app: Litestar,
    rev_range: str | None = None,
    verbose: bool = False,
    indicate_current: bool = False,
) -> None:
    """List changeset scripts in chronological order."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.history(
        config=alembic_cfg, rev_range=rev_range, verbose=verbose, indicate_current=indicate_current
    )


def merge(
    app: Litestar,
    revisions: str,
    message: str | None = None,
    branch_label: str | None = None,
    rev_id: str | None = None,
) -> None:
    """Merge two revisions together. Creates a new migration file."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.merge(
        config=alembic_cfg, revisions=revisions, message=message, branch_label=branch_label, rev_id=rev_id
    )


def revision(
    app: Litestar,
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
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
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


def show(
    app: Litestar,
    rev: Any,
) -> None:
    """Show the revision(s) denoted by the given symbol."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.show(config=alembic_cfg, rev=rev)  # type: ignore[no-untyped-call]


def init(
    app: Litestar,
    directory: str,
    template_path: str | None = None,
    package: bool = False,
    multidb: bool = False,
) -> None:
    """Initialize a new scripts directory."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)

    template = "sync"
    if isinstance(plugin._config, SQLAlchemyAsyncConfig):
        template = "asyncio"
    if multidb:
        template = f"{template}-multidb"
        raise NotImplementedError("Multi database Alembic configurations are not currently supported.")
    if template_path is None:
        template_path = f"{Path(__file__).parent}/templates"
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.init(
        config=alembic_cfg,
        directory=directory,
        template=template,
        package=package,
    )


def list_templates(app: Litestar) -> None:
    """List available templates."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.list_templates(config=alembic_cfg)


def stamp(
    app: Litestar,
    revision: str,
    sql: bool = False,
    tag: str | None[str] = None,
    purge: bool = False,
) -> None:
    """'stamp' the revision table with the given revision; don't run any migrations."""
    plugin = app.plugins.get(SQLAlchemyInitPlugin)
    alembic_cfg = get_alembic_command_config(config=plugin._config)
    migration_command.stamp(config=alembic_cfg, revision=revision, sql=sql, tag=tag, purge=purge)
