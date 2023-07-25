from typing import TYPE_CHECKING
import sys
from rich.prompt import Confirm

from litestar.cli._utils import RICH_CLICK_INSTALLED, LitestarGroup
from litestar.contrib.sqlalchemy import utils as db_utils

if TYPE_CHECKING or not RICH_CLICK_INSTALLED:
    from click import argument, group, option, BOOL, echo
else:
    from rich_click import argument, group, option, BOOL


@group(cls=LitestarGroup, name="db")
def database_group() -> None:
    """Manage SQLAlchemy database components."""


@database_group.command(
    name="migrate",
    help="Executes migrations to apply any outstanding database structures.",
)
def upgrade_database() -> None:
    """Upgrade the database to the latest revision."""
    import anyio

    anyio.run(db_utils.upgrade_database)


@database_group.command(
    name="reset",
    help="Drop all objects and create a fresh database.",
)
@option(
    "--no-prompt",
    help="Do not prompt for confirmation.",
    type=BOOL,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def reset_database(no_prompt: bool) -> None:
    """Reset the database to an initial empty state."""
    import anyio

    if not no_prompt:
        Confirm.ask("Are you sure you want to drop and recreate everything?")
    anyio.run(reset_database)


@database_group.command(
    name="destroy",
    help="Drops all tables.",
)
@option(
    "--no-prompt",
    help="Do not prompt for confirmation.",
    type=BOOL,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def destroy_database(no_prompt: bool) -> None:
    """Drop all objects in the database."""
    import anyio

    if not no_prompt:
        confirmed = Confirm.ask(
            "Are you sure you want to drop everything?",
        )
        if not confirmed:
            echo("Aborting database purge and exiting.")
            sys.exit(0)
    anyio.run(db_utils.purge_database)


@database_group.command(
    name="current-revision",
    help="Shows the current revision for the database.",
)
def show_database_revision() -> None:
    """Show current database revision."""
    import anyio

    anyio.run(db_utils.show_database_revision)
