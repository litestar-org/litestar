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


@database_group.command(
    name="revision",
    help="Create a new migration revision.",
)
@option("-m", "--message", default=None, help="Revision message")
@option("--autogenerate", is_flag=True, default=True, help="Automatically populate revision with detected changes")
@option("--sql", is_flag=True, default=False, help="Export to `.sql` instead of writing to the database.")
@option("--head", default="head", help="Specify head revision to use as base for new revision.")
@option("--splice", is_flag=True, default=False, help='Allow a non-head revision as the "head" to splice onto')
@option("--branch-label", default=None, help="Specify a branch label to apply to the new revision")
@option("--version-path", default=None, help="Specify specific path from config for version file")
@option("--rev-id", default=None, help="Specify a ID to use for revision.")
def create_revision(
    app: Litestar,
    message: str | None,
    autogenerate: bool,
    sql: bool,
    head: str,
    splice: bool,
    branch_label: str | None,
    version_path: str | None,
    rev_id: str | None,
) -> None:
    """Create a new database revision."""
    db_utils.revision(
        app=app,
        message=message,
        autogenerate=autogenerate,
        sql=sql,
        head=head,
        splice=splice,
        branch_label=branch_label,
        version_path=version_path,
        rev_id=rev_id,
    )
