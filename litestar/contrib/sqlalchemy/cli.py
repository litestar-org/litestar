from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.cli._utils import RICH_CLICK_INSTALLED, LitestarGroup
from litestar.contrib.sqlalchemy.alembic import commands as db_utils

if TYPE_CHECKING:
    from litestar import Litestar


if TYPE_CHECKING or not RICH_CLICK_INSTALLED:
    from click import group, option
else:
    from rich_click import group, option


@group(cls=LitestarGroup, name="database")
def database_group() -> None:
    """Manage SQLAlchemy database components."""


@database_group.command(
    name="current-revision",
    help="Shows the current revision for the database.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def show_database_revision(app: Litestar, verbose: bool) -> None:
    """Show current database revision."""

    db_utils.current(app=app, verbose=verbose)


@database_group.command(
    name="downgrade",
    help="Downgrade database to a specific revision.",
)
@option(
    "--revision",
    type=str,
    help="Revision to upgrade to",
    default="-1",
)
@option("--sql", type=bool, help="Generate SQL output for offline migrations.", default=False, is_flag=True)
@option(
    "--tag",
    help="an arbitrary 'tag' that can be intercepted by custom env.py scripts via the .EnvironmentContext.get_tag_argument method.",
    type=str,
    default=None,
)
def downgrade_database(app: Litestar, revision: str, sql: bool, tag: str | None) -> None:
    """Downgrade the database to the latest revision."""

    db_utils.downgrade(app=app, revision=revision, sql=sql, tag=tag)


@database_group.command(
    name="upgrade",
    help="Upgrade database to a specific revision.",
)
@option(
    "--revision",
    type=str,
    help="Revision to upgrade to",
    default="head",
)
@option("--sql", type=bool, help="Generate SQL output for offline migrations.", default=False, is_flag=True)
@option(
    "--tag",
    help="an arbitrary 'tag' that can be intercepted by custom env.py scripts via the .EnvironmentContext.get_tag_argument method.",
    type=str,
    default=None,
)
def upgrade_database(app: Litestar, revision: str, sql: bool, tag: str | None) -> None:
    """Upgrade the database to the latest revision."""

    db_utils.upgrade(app=app, revision=revision, sql=sql, tag=tag)


@database_group.command(
    name="init",
    help="Initialize migrations for the project.",
)
@option(
    "-d", "--directory", default="migrations", help="Location to save migration scripts.  The default is 'migrations/'"
)
@option("--multidb", is_flag=True, default=False, help="Support multiple databases")
@option("--package", is_flag=True, default=True, help="Create `__init__.py` for created folder")
def init_alembic(app: Litestar, directory: str, multidb: bool, package: bool) -> None:
    """Upgrade the database to the latest revision."""

    db_utils.init(app=app, directory=directory, multidb=multidb, package=package)
