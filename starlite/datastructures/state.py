from copy import copy
from typing import Any, Dict, Iterator, MutableMapping, Optional


class State(MutableMapping[str, Any]):
    """An object meant to store arbitrary state.

    It can be accessed using dot notation while exposing dict like functionalities.
    """

    __slots__ = ("_state",)

    _state: Dict[str, Any]

    def __init__(self, state: Optional[Dict[str, Any]] = None) -> None:
        """Initialize `State` with an optional value.

        Args:
             state: An optional string keyed dict for the initial state.

        Examples:
        ```python
        from starlite import State

        state_dict = {"first": 1, "second": 2, "third": 3, "fourth": 4}
        state = State(state_dict)

        # state can be accessed using '.' notation
        assert state.fourth == 4
        del state.fourth

        # state implements the Mapping type:
        assert len(state) == 3
        assert "first" in state
        assert not "fourth" in state
        assert state["first"] == 1
        assert [(k, v) for k, v in state.items()] == [("first", 1), ("second", 2), ("third", 3)]

        state["fourth"] = 4
        assert "fourth" in state
        del state["fourth"]

        # state implements __bool__
        assert state  # state is true when it has values.
        assert not State()  # state is empty when it has no values.

        # it has shallow copy
        copied_state = state.copy()
        del copied_state.first
        assert state.first

        # it has a 'dict' method to retrieve a shallow copy of the underlying dict
        inner_dict = state.dict()
        assert inner_dict == state_dict
        ```
        """
        super().__setattr__("_state", state if state is not None else {})

    def __bool__(self) -> bool:
        """Return a boolean indicating whether the wrapped dict instance has values."""
        return bool(self._state)

    def __getitem__(self, key: str) -> Any:
        """Get the value for the corresponding key from the wrapped state object using subscription notation.

        Args:
            key: Key to access.

        Raises:
            KeyError

        Returns:
            A value from the wrapped state instance.
        """
        return self._state[key]

    def __delitem__(self, key: str) -> None:
        """Delete the value from the key from the wrapped state object using subscription notation.

        Args:
            key: Key to delete

        Raises:
            KeyError: if the given attribute is not set.

        Returns:
            None
        """
        del self._state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an item in the state using subscription notation.

        Args:
            key: Key to set.
            value: Value to set.

        Returns:
            None
        """
        self._state[key] = value

    def __iter__(self) -> Iterator[str]:
        """Return an iterator iterating the wrapped state dict.

        Returns:
            An iterator of strings
        """
        return iter(self._state)

    def __len__(self) -> int:
        """Return length of the wrapped state dict.

        Returns:
            An integer
        """
        return len(self._state)

    def __setattr__(self, key: str, value: Any) -> None:
        """Set an item in the state using attribute notation.

        Args:
            key: Key to set.
            value: Value to set.

        Returns:
            None
        """
        self._state[key] = value

    def __getattr__(self, key: str) -> Any:
        """Get the value for the corresponding key from the wrapped state object using attribute notation.

        Args:
            key: Key to retrieve

        Raises:
            AttributeError: if the given attribute is not set.

        Returns:
            The retrieved value
        """
        try:
            return self._state[key]
        except KeyError as e:
            raise AttributeError(f"State instance has no attribute '{key}'") from e

    def __delattr__(self, key: str) -> None:
        """Delete the value from the key from the wrapped state object using attribute notation.

        Args:
            key: Key to delete

        Raises:
            AttributeError: if the given attribute is not set.

        Returns:
            None
        """
        try:
            del self._state[key]
        except KeyError as e:
            raise AttributeError(f"State instance has no attribute '{key}'") from e

    def __copy__(self) -> "State":
        """Return a shallow copy of the given state object.

        Customizes how the builtin "copy" function will work.
        """
        return self.__class__(copy(self._state))

    def copy(self) -> "State":
        """Return a shallow copy of 'self'.

        Returns:
            A `State`
        """
        return copy(self)

    def dict(self) -> Dict[str, Any]:
        """Return a shallow copy of the wrapped dict.

        Returns:
            A dict
        """
        return copy(self._state)
