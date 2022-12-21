from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from click import Group

    CLIInitCallback = Callable[[Group], Any]

T = TypeVar("T", bound="CLIInitCallback")

CLI_INIT_CALLBACKS: list[CLIInitCallback] = []


def on_cli_init(func: T) -> T:
    """Register a function to run after the CLI has been initiated. Do nothing if `starlite-cli` is not installed.

    Args:
        func: A callable that will receive the main `Group` as its first argument
    """
    CLI_INIT_CALLBACKS.append(func)
    return func
