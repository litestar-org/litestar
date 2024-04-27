from __future__ import annotations

import pytest

from litestar.handlers import delete, get, head, patch, post, put


@pytest.mark.parametrize("handler_cls", [get, post, put, patch, delete, head])
def test_subclass_warns_deprecation(handler_cls: get | post | put | patch | delete | head) -> None:
    with pytest.warns(DeprecationWarning):

        class SubClass(handler_cls):
            pass
