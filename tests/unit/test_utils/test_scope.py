from typing import TYPE_CHECKING, Callable

import pytest

from litestar.utils import (
    get_litestar_scope_state,
    set_litestar_scope_state,
)

if TYPE_CHECKING:
    from litestar.types.asgi_types import Scope


@pytest.fixture()
def scope(create_scope: "Callable[..., Scope]") -> "Scope":
    return create_scope()


def test_get_litestar_scope_state_removes_value_from_state(scope: "Scope") -> None:
    key = "test"
    value = {"key": "value"}
    set_litestar_scope_state(scope, key, value)
    retrieved_value = get_litestar_scope_state(scope, key, pop=True)
    assert retrieved_value == value
    assert get_litestar_scope_state(scope, key) is None


def test_set_litestar_scope_state(scope: "Scope") -> None:
    set_litestar_scope_state(scope, "key", "value")
    assert get_litestar_scope_state(scope, "key") == "value"
