from typing import Final, NoReturn

try:
    import rich_click as click
except ImportError:
    import click  # type: ignore[no-redef]

_SUGGEST_OPTION_POSSIBILITIES: Final = {
    "-V": ["command `version`"],
    "--version": ["command `version`"],
}


def suggest_option(error: click.NoSuchOption) -> NoReturn:
    if error.possibilities:
        raise error

    new_possibilities = _SUGGEST_OPTION_POSSIBILITIES.get(error.option_name)
    if new_possibilities is None:
        raise error

    new_error = click.NoSuchOption(
        option_name=error.option_name,
        possibilities=new_possibilities,
        message=error.message,
        ctx=error.ctx,
    )
    raise new_error from error
