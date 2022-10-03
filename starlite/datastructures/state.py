from copy import copy
from typing import Any, Dict, Iterator, MutableMapping, Optional


class State(MutableMapping[str, Any]):

    __slots__ = ("_state",)

    _state: Dict[str, Any]

    def __init__(self, state: Optional[Dict[str, Any]] = None) -> None:
        """An object meant to store arbitrary state. It can be accessed using
        dot notation while exposing dict like functionalities.

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
        """

        Returns:
            Boolean indicating whether the wrapped dict instance has values.
        """
        return bool(self._state)

    def __getitem__(self, key: str) -> Any:
        """

        Args:
            key: Key to access.

        Raises:
            KeyError

        Returns:
            A value from the wrapped state instance.
        """
        return self._state[key]

    def __delitem__(self, key: str) -> None:
        """
        Args:
            key: Key to access.

        Raises:
            KeyError

        Returns:
            None
        """
        del self._state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """

        Args:
            key: Key to set.
            value: Value to set.

        Returns:
            None
        """
        self._state[key] = value

    def __iter__(self) -> Iterator[str]:
        """

        Returns:
            An iterator iterating the wrapped state dict.
        """
        return iter(self._state)

    def __len__(self) -> int:
        """

        Returns:
            The length of the wrapped state dict.
        """
        return len(self._state)

    def __setattr__(self, key: str, value: Any) -> None:
        """

        Args:
            key: Key to set.
            value: Value to set.

        Returns:
            None
        """
        self._state[key] = value

    def __getattr__(self, key: str) -> Any:
        """

        Args:
            key: Key to retrieve

        Raises:
            AttributeError: if the given attribute is not set.

        Returns:
            Retrieves the value for the corresponding key from the wrapped state object.
        """
        try:
            return self._state[key]
        except KeyError as e:
            raise AttributeError(f"State instance has no attribute '{key}'") from e

    def __delattr__(self, key: str) -> None:
        """

        Args:
            key: Key to delete

        Raises:
            AttributeError: if the given attribute is not set.

        Returns:
            Deletes the value from the key from the wrapped state object.
        """
        try:
            del self._state[key]
        except KeyError as e:
            raise AttributeError(f"State instance has no attribute '{key}'") from e

    def __copy__(self) -> "State":
        """Returns a shallow copy of the given state object.

        Customizes how the builtin "copy" function will work.
        """
        return self.__class__(copy(self._state))

    def copy(self) -> "State":
        """

        Returns:
            A shallow copy of 'self'.
        """
        return copy(self)

    def dict(self) -> Dict[str, Any]:
        """

        Returns:
            A shallow copy of the wrapped dict.
        """
        return copy(self._state)
