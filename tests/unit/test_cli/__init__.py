APP_FILE_CONTENT = """
from litestar import Litestar
app = Litestar([])
"""


CREATE_APP_FILE_CONTENT = """
from litestar import Litestar

def create_app():
    return Litestar([])


def func():
    return False
"""


GENERIC_APP_FACTORY_FILE_CONTENT = """
from litestar import Litestar

def any_name() -> Litestar:
    return Litestar([])


def func():
    return False
"""

GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION = """
from litestar import Litestar

def any_name() -> "Litestar":
    return Litestar([])


def func():
    return False
"""


GENERIC_APP_FACTORY_FILE_CONTENT_FUTURE_ANNOTATIONS = """
from __future__ import annotations

from litestar import Litestar

def any_name() -> Litestar:
    return Litestar([])


def func():
    return False
"""


APP_FACTORY_FILE_CONTENT_SERVER_LIFESPAN_PLUGIN = """
from contextlib import contextmanager
from typing import Generator

from litestar import Litestar
from litestar.config.app import AppConfig
from litestar.plugins.base import CLIPlugin


class StartupPrintPlugin(CLIPlugin):

    @contextmanager
    def server_lifespan(self, app: Litestar) -> Generator[None, None, None]:
        print("i_run_before_startup_plugin")  # noqa: T201
        try:
            yield
        finally:
            print("i_run_after_shutdown_plugin")  # noqa: T201

def create_app() -> Litestar:
    return Litestar(route_handlers=[], plugins=[StartupPrintPlugin()])

"""
