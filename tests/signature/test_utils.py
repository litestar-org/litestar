from __future__ import annotations

from typing import Any

import pytest

from litestar._signature.parsing.utils import get_fn_type_hints
from litestar.file_system import BaseLocalFileSystem
from litestar.static_files import StaticFiles
from litestar.types.asgi_types import Receive, Scope, Send
from litestar.types.builtin_types import NoneType


def test_get_fn_type_hints_asgi_app() -> None:
    app = StaticFiles(is_html_mode=False, directories=[], file_system=BaseLocalFileSystem())
    assert get_fn_type_hints(app) == {"scope": Scope, "receive": Receive, "send": Send, "return": NoneType}


def func(a: int, b: str, c: float) -> None:
    ...


class C:
    def __init__(self, a: int, b: str, c: float) -> None:
        ...

    def method(self, a: int, b: str, c: float) -> None:
        ...

    def __call__(self, a: int, b: str, c: float) -> None:
        ...


@pytest.mark.parametrize("fn", [func, C, C(1, "2", 3.0).method, C(1, "2", 3.0)])
def test_get_fn_type_hints(fn: Any) -> None:
    assert get_fn_type_hints(fn) == {"a": int, "b": str, "c": float, "return": NoneType}
