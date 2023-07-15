from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ._utils import RICH_CLICK_INSTALLED, LitestarEnv, LitestarExtensionGroup
from .commands import core, schema, sessions

if TYPE_CHECKING or not RICH_CLICK_INSTALLED:
    import click
    from click import Context, group, option, pass_context
    from click import Path as ClickPath
else:
    import rich_click as click
    from rich_click import Context, group, option, pass_context
    from rich_click import Path as ClickPath
    from rich_click.cli import patch as rich_click_patch

    rich_click_patch()
    click.rich_click.USE_RICH_MARKUP = True
    click.rich_click.USE_MARKDOWN = False
    click.rich_click.SHOW_ARGUMENTS = True
    click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
    click.rich_click.SHOW_ARGUMENTS = True
    click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
    click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"
    click.rich_click.ERRORS_SUGGESTION = ""
    click.rich_click.ERRORS_EPILOGUE = ""
    click.rich_click.MAX_WIDTH = 100
    click.rich_click.SHOW_METAVARS_COLUMN = True
    click.rich_click.APPEND_METAVARS_HELP = True


__all__ = ("litestar_group",)


@group(cls=LitestarExtensionGroup)
@option("--app", "app_path", help="Module path to a Litestar application")
@option(
    "--app-dir",
    help="Look for APP in the specified directory, by adding this to the PYTHONPATH. Defaults to the current working directory.",
    default=None,
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    show_default=False,
)
@pass_context
def litestar_group(ctx: Context, app_path: str | None, app_dir: Path | None = None) -> None:
    """Litestar CLI."""
    sys.path.append(str(app_dir))
    ctx.obj = lambda: LitestarEnv.from_env(app_path)


# add sub commands here

litestar_group.add_command(core.info_command)
litestar_group.add_command(core.run_command)
litestar_group.add_command(core.routes_command)
litestar_group.add_command(core.version_command)
litestar_group.add_command(sessions.sessions_group)
litestar_group.add_command(schema.schema_group)
