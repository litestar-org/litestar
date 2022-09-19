from cleo.application import Application
from cleo.testers.command_tester import CommandTester

from commands.list_routes import ListRoutes
from starlite import Starlite


def test_command_routes() -> None:
    application = Application()
    app = Starlite(route_handlers=[])
    application.add(ListRoutes(app))

    command = application.find("routes")
    command_tester = CommandTester(command)
    command_tester.execute()

    assert "'GET'" in command_tester.io.fetch_output()
