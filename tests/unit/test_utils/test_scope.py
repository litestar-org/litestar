from typing import TYPE_CHECKING

import pytest

from litestar.constants import SCOPE_STATE_NAMESPACE
from litestar.utils import (
    get_litestar_scope_state,
    set_litestar_scope_state,
)

if TYPE_CHECKING:
    from litestar.types.asgi_types import HTTPScope


@pytest.fixture()
def scope() -> "HTTPScope":
    return {"state": {}}  # type:ignore[typeddict-item]


def test_get_litestar_scope_state_without_default_does_not_set_key_in_scope_state(scope: "HTTPScope") -> None:
    get_litestar_scope_state(scope, "key")
    assert SCOPE_STATE_NAMESPACE in scope["state"]
    assert "key" not in scope["state"][SCOPE_STATE_NAMESPACE]


def test_get_litestar_scope_state_with_default_does_not_set_key_in_scope_state(scope: "HTTPScope") -> None:
    value = get_litestar_scope_state(scope, "key", "value")
    assert SCOPE_STATE_NAMESPACE in scope["state"]
    assert value == "value"
    assert "key" not in scope["state"][SCOPE_STATE_NAMESPACE]


def test_get_litestar_scope_state_removes_value_from_state(scope: "HTTPScope") -> None:
    key = "test"
    value = {"key": "value"}
    scope["state"][SCOPE_STATE_NAMESPACE] = {key: value}
    retrieved_value = get_litestar_scope_state(scope, key, pop=True)
    assert retrieved_value == value
    assert key not in scope["state"][SCOPE_STATE_NAMESPACE]


def test_set_litestar_scope_state(scope: "HTTPScope") -> None:
    set_litestar_scope_state(scope, "key", "value")
    assert scope["state"][SCOPE_STATE_NAMESPACE]["key"] == "value"
