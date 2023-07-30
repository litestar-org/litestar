from __future__ import annotations

from typing import TYPE_CHECKING

import anyio

from litestar.cli._utils import RICH_CLICK_INSTALLED, LitestarGroup
from litestar.contrib.sqlalchemy.alembic import commands as db_utils
from litestar.exceptions import LitestarException

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.contrib.sqlalchemy.plugins.init.config.alembic import AlembicConfig


if TYPE_CHECKING or not RICH_CLICK_INSTALLED:
    from click import group
else:
    from rich_click import group


@group(cls=LitestarGroup, name="db")
def database_group() -> None:
    """Manage SQLAlchemy database components."""


@database_group.command(
    name="migrate",
    help="Apply migrations to a database.",
)
def upgrade_database(app: Litestar) -> None:
    """Upgrade the database to the latest revision."""

    config: AlembicConfig | None = None
    for cli_plugin in app.cli_plugins:
        if hasattr(cli_plugin, "_alembic_config"):
            config = cli_plugin._alembic_config
    if config is None:
        raise LitestarException("Could not find SQLAlchemy configuration.")

    anyio.run(db_utils.upgrade, config.alembic_config, config.script_location)


@database_group.command(
    name="downgrade",
    help="Downgrade database to a specific revision.",
)
def downgrade_database(app: Litestar) -> None:
    """Upgrade the database to the latest revision."""

    config: AlembicConfig | None = None
    for cli_plugin in app.cli_plugins:
        if hasattr(cli_plugin, "_alembic_config"):
            config = cli_plugin._alembic_config
    if config is None:
        raise LitestarException("Could not find SQLAlchemy configuration.")
    anyio.run(db_utils.downgrade, config.alembic_config, config.script_location)


@database_group.command(
    name="current-revision",
    help="Shows the current revision for the database.",
)
def show_database_revision(app: Litestar) -> None:
    """Show current database revision."""

    config: AlembicConfig | None = None
    for cli_plugin in app.cli_plugins:
        if hasattr(cli_plugin, "_alembic_config"):
            config = cli_plugin._alembic_config
    if config is None:
        raise LitestarException("Could not find SQLAlchemy configuration.")
    anyio.run(db_utils.current)
