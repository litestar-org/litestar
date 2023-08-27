from __future__ import annotations

import pkgutil
from typing import TYPE_CHECKING

from litestar.plugins import CLIPluginProtocol, InitPluginProtocol

from .cli import run_command

if TYPE_CHECKING:
    from click import Group


class SlotsBase:
    __slots__ = ()


class SocketifyPlugin(InitPluginProtocol, CLIPluginProtocol, SlotsBase):
    """Socketify server plugin."""

    def on_cli_init(self, cli: Group) -> None:
        if pkgutil.find_loader("click") is not None:
            from litestar.cli.main import litestar_group as cli

            cli.add_command(run_command)
        return super().on_cli_init(cli)
