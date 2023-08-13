from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.cli._utils import RICH_CLICK_INSTALLED, LitestarGroup
from litestar.contrib.sqlalchemy.alembic.commands import AlembicCommands

if TYPE_CHECKING:
    from litestar import Litestar


if TYPE_CHECKING or not RICH_CLICK_INSTALLED:
    from click import confirm, group, option, prompt
else:
    from rich_click import group, option


@group(cls=LitestarGroup, name="database")
def database_group() -> None:
    """Manage SQLAlchemy database components."""


@database_group.command(
    name="show-current-revision",
    help="Shows the current revision for the database.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def show_database_revision(app: Litestar, verbose: bool) -> None:
    """Show current database revision."""
    alembic_commands = AlembicCommands(app=app)
    alembic_commands.current(verbose=verbose)


@database_group.command(
    name="downgrade",
    help="Downgrade database to a specific revision.",
)
@option(
    "--revision",
    type=str,
    help="Revision to downgrade to",
    default="-1",
)
@option("--sql", type=bool, help="Generate SQL output for offline migrations.", default=False, is_flag=True)
@option(
    "--tag",
    help="an arbitrary 'tag' that can be intercepted by custom env.py scripts via the .EnvironmentContext.get_tag_argument method.",
    type=str,
    default=None,
)
@option(
    "--no-prompt",
    help="Do not prompt for confirmation before downgrading.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def downgrade_database(app: Litestar, revision: str, sql: bool, tag: str | None, no_prompt: bool) -> None:
    """Downgrade the database to the latest revision."""
    input_confirmed = True if no_prompt else confirm("Are you sure you you want to downgrade the database?")
    if input_confirmed:
        alembic_commands = AlembicCommands(app=app)
        alembic_commands.downgrade(revision=revision, sql=sql, tag=tag)


@database_group.command(
    name="migrate",
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
@option(
    "--no-prompt",
    help="Do not prompt for confirmation before upgrading.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def upgrade_database(app: Litestar, revision: str, sql: bool, tag: str | None, no_prompt: bool) -> None:
    """Upgrade the database to the latest revision."""
    input_confirmed = True if no_prompt else confirm("Are you sure you you want to apply migrations?")
    if input_confirmed:
        alembic_commands = AlembicCommands(app=app)
        alembic_commands.upgrade(revision=revision, sql=sql, tag=tag)


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
    alembic_commands = AlembicCommands(app=app)
    alembic_commands.init(directory=directory, multidb=multidb, package=package)


@database_group.command(
    name="make-migrations",
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
@option(
    "--no-prompt",
    help="Do not prompt for a migration message.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
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
    no_prompt: bool,
) -> None:
    """Create a new database revision."""
    if message is None and no_prompt:
        message = "autogenerated"
    elif message is None and not no_prompt:
        message = prompt("Please enter a message describing this revision:")
    alembic_commands = AlembicCommands(app=app)
    alembic_commands.revision(
        message=message,
        autogenerate=autogenerate,
        sql=sql,
        head=head,
        splice=splice,
        branch_label=branch_label,
        version_path=version_path,
        rev_id=rev_id,
    )


@database_group.command(
    name="merge-migrations",
    help="Merge multiple revisions into a single new revision.",
)
@option("--revisions", default="head", help="Specify head revision to use as base for new revision.")
@option("-m", "--message", default=None, help="Revision message")
@option("--branch-label", default=None, help="Specify a branch label to apply to the new revision")
@option("--rev-id", default=None, help="Specify a ID to use for revision.")
@option(
    "--no-prompt",
    help="Do not prompt for a migration message.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def merge_revisions(
    app: Litestar, revisions: str, message: str | None, branch_label: str | None, rev_id: str | None, no_prompt: bool
) -> None:
    """Create a new database revision."""
    if message is None and no_prompt:
        message = "autogenerated"
    elif message is None and not no_prompt:
        message = prompt("Please enter a message describing this revision:")

    alembic_commands = AlembicCommands(app=app)
    alembic_commands.merge(message=message, revisions=revisions, branch_label=branch_label, rev_id=rev_id)


@database_group.command(
    name="stamp-migration",
    help="Mark (Stamp) a specific revision as current without applying the migrations.",
)
@option(
    "--revision",
    type=str,
    help="Revision to stamp to",
    default="-1",
)
@option("--sql", type=bool, help="Generate SQL output for offline migrations.", default=False, is_flag=True)
@option(
    "--purge",
    type=bool,
    help="Delete existing records in the alembic version table before stamping.",
    default=False,
    is_flag=True,
)
@option(
    "--tag",
    help="an arbitrary 'tag' that can be intercepted by custom env.py scripts via the .EnvironmentContext.get_tag_argument method.",
    type=str,
    default=None,
)
@option(
    "--no-prompt",
    help="Do not prompt for confirmation.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def stamp_revision(app: Litestar, revision: str, sql: bool, tag: str | None, purge: bool, no_prompt: bool) -> None:
    """Create a new database revision."""
    input_confirmed = True if no_prompt else confirm("Are you sure you you want to stamp revision?")
    if input_confirmed:
        alembic_commands = AlembicCommands(app=app)
        alembic_commands.stamp(sql=sql, revision=revision, tag=tag, purge=purge)
