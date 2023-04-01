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
