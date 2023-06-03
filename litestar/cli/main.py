from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ._utils import LitestarEnv, LitestarExtensionGroup
from .commands import core, schema, sessions

if TYPE_CHECKING:
    import click
    from click import Context, group, option, pass_context
    from click import Path as ClickPath
else:
    try:
        import rich_click as click
        from rich_click import Context, group, option, pass_context
        from rich_click import Path as ClickPath
        from rich_click.cli import patch as rich_click_patch

        rich_click_patch()  # pyright: ignore[reportUnboundVariable]
        click.rich_click.USE_RICH_MARKUP = True  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.USE_MARKDOWN = False  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.SHOW_ARGUMENTS = True  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.GROUP_ARGUMENTS_OPTIONS = True  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.SHOW_ARGUMENTS = True  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.GROUP_ARGUMENTS_OPTIONS = True  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.ERRORS_SUGGESTION = ""  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.ERRORS_EPILOGUE = ""  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.MAX_WIDTH = 100  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.SHOW_METAVARS_COLUMN = True  # pyright: ignore[reportGeneralTypeIssues]
        click.rich_click.APPEND_METAVARS_HELP = True  # pyright: ignore[reportGeneralTypeIssues]
    except ImportError:
        import click
        from click import Context, group, option, pass_context
        from click import Path as ClickPath


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
