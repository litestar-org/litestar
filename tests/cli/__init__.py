APP_FILE_CONTENT = """
from starlite import Starlite
app = Starlite([])
"""


CREATE_APP_FILE_CONTENT = """
from starlite import Starlite

def create_app():
    return Starlite([])


def func():
    return False
"""


GENERIC_APP_FACTORY_FILE_CONTENT = """
from starlite import Starlite

def any_name() -> Starlite:
    return Starlite([])


def func():
    return False
"""

GENERIC_APP_FACTORY_FILE_CONTENT_STRING_ANNOTATION = """
from starlite import Starlite

def any_name() -> "Starlite":
    return Starlite([])


def func():
    return False
"""


GENERIC_APP_FACTORY_FILE_CONTENT_FUTURE_ANNOTATIONS = """
from __future__ import annotations

from starlite import Starlite

def any_name() -> Starlite:
    return Starlite([])


def func():
    return False
"""
