from inspect import getfullargspec
from typing import TYPE_CHECKING

from cleo.application import Application

import commands

if TYPE_CHECKING:
    from starlite.app import Starlite


class Cli:
    """CLI Add CLI commands using cleo https://github.com/python-poetry/cleo .
    New commands should be placed in the commands folder and added in
    __init__.py. usage example:

    # ...
    app = Starlite(route_handlers=[hello_world])
    if __name__ == '__main__':
        from commands.cli import Cli
        cli = Cli(app)
        cli.run()
    """

    def __init__(self, app: "Starlite"):
        self.st_app = app
        self.cli_ = Application()
        for command in commands.__all__:
            cli_command = getattr(commands, command)

            arg_spec = getfullargspec(cli_command)
            if "app" in arg_spec.args:
                self.cli_.add(cli_command(self.st_app))
            else:
                self.cli_.add(cli_command())  # pylint: disable = no-value-for-parameter

    def run(self) -> int:
        """start Cleo."""
        errorcode: int = self.cli_.run()
        return errorcode
