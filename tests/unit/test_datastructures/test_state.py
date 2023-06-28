from __future__ import annotations

from copy import copy
from typing import Any

import pytest

from litestar.datastructures import State
from litestar.datastructures.state import ImmutableState


@pytest.mark.parametrize("state_class", (ImmutableState, State))
def test_state_immutable_mapping(state_class: type[ImmutableState]) -> None:
    state_dict = {"first": 1, "second": 2, "third": 3}
    state = state_class(state_dict, deep_copy=True)
    assert len(state) == 3
    assert "first" in state
    assert state["first"] == 1
    assert list(state.items()) == [("first", 1), ("second", 2), ("third", 3)]
    assert state
    assert isinstance(state.mutable_copy(), State)
    del state_dict["first"]
    assert "first" in state


@pytest.mark.parametrize(
    "zero_object", (ImmutableState({"first": 1}), State({"first": 1}), {"first": 1}, [("first", 1)])
)
def test_state_init(zero_object: Any) -> None:
    state = ImmutableState(zero_object)
    assert state.first


@pytest.mark.parametrize("zero_object", (ImmutableState({}), State(), {}, [], None))
def test_state_mapping(zero_object: Any) -> None:
    state = State(zero_object)
    assert not state
    state["first"] = "first"
    state["second"] = "second"
    assert state.first == "first"
    assert state["second"] == "second"
    del state["first"]
    del state.second
    assert "first" not in state
    assert "second" not in state
    assert isinstance(state.immutable_copy(), ImmutableState)


def test_state_attributes() -> None:
    state_dict = {"first": 1, "second": 2, "third": 3}
    state = State(state_dict)
    assert state.first == 1
    del state.first
    with pytest.raises(AttributeError):
        assert state.first
    state.fourth = 4
    assert state.fourth == 4
    with pytest.raises(AttributeError):
        del state.first


def test_state_dict() -> None:
    state_dict = {"first": 1, "second": 2, "third": 3}
    state = State(state_dict)
    assert state.dict() == state_dict


def test_state_copy() -> None:
    state_dict = {"key": {"inner": 1}}
    state = State(state_dict)
    copy = state.copy()
    del state.key
    assert copy.key


def test_state_copy_deep_copy_false() -> None:
    state = State({}, deep_copy=False)
    assert state.copy()._deep_copy is False


def test_unpicklable_deep_copy_false() -> None:
    # a module cannot be deep copied
    import typing

    state = ImmutableState({"module": typing}, deep_copy=False)
    copy(state)
    ImmutableState.validate(state)
