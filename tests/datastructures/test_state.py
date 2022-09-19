import pytest

from starlite.datastructures import State


def test_state_mapping() -> None:
    state_dict = {"first": 1, "second": 2, "third": 3}
    state = State(state_dict)

    assert len(state) == 3
    assert "first" in state
    assert "fourth" not in state
    assert state["first"] == 1
    assert [(k, v) for k, v in state.items()] == [("first", 1), ("second", 2), ("third", 3)]
    assert state
    assert not State()


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
