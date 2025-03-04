from __future__ import annotations

from importlib import reload
from warnings import catch_warnings, simplefilter

import pytest

from litestar.handlers import delete, get, head, patch, post, put


@pytest.mark.parametrize("handler_cls", [get, post, put, patch, delete, head])
def test_subclass_warns_deprecation(handler_cls: get | post | put | patch | delete | head) -> None:
    with pytest.warns(DeprecationWarning):

        class SubClass(handler_cls):  # type: ignore[valid-type, misc]
            pass


def test_default_no_warns() -> None:
    with catch_warnings(record=True) as warnings:
        simplefilter("always")
        import litestar.handlers.http_handlers.decorators

        reload(litestar.handlers.http_handlers.decorators)
        assert len(warnings) == 0

        # revert to previous filter
        simplefilter("default")
