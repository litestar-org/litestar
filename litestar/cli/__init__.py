"""Litestar CLI."""

from __future__ import annotations

from importlib.util import find_spec

if find_spec("rich_click") is not None:  # pragma: no cover
    import rich_click

    rich_click.rich_click.THEME = "star-box"
    rich_click.rich_click.TEXT_MARKUP = "rich"
    rich_click.rich_click.SHOW_ARGUMENTS = True
    rich_click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
    rich_click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"
    rich_click.rich_click.ERRORS_SUGGESTION = ""
    rich_click.rich_click.ERRORS_EPILOGUE = ""
    rich_click.rich_click.MAX_WIDTH = 120
    # replaces 'SHOW_METAVARS_COLUMN' / 'APPEND_METAVARS_HELP'; 'opt_long' precedes
    # 'opt_short' to keep the long form in the first column, as it has always rendered.
    rich_click.rich_click.OPTIONS_TABLE_COLUMN_TYPES = ["opt_long", "opt_short", "metavar", "help"]
    rich_click.rich_click.OPTIONS_TABLE_HELP_SECTIONS = [
        "help",
        "deprecated",
        "envvar",
        "default",
        "required",
        "metavar",
    ]


from .main import litestar_group

__all__ = ["litestar_group"]
