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


APP_FACTORY_FILE_CONTENT_STARTUP_SHUTDOWN_HOOKS = """
from litestar import Litestar

def before_startup_function() -> None:
    print("i_run_before_startup")

def after_shutdown_function() -> None:
    print("i_run_after_shutdown")

def create_app() -> Litestar:
    return Litestar(
        [],
        on_cli_startup=[before_startup_function],
        on_cli_shutdown=[after_shutdown_function],
    )
"""
