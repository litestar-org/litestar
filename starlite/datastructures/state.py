from copy import copy
from threading import RLock
from typing import Any, Dict, Iterable, Iterator, MutableMapping, Optional, Tuple, Union


class State(MutableMapping[str, Any]):
    """An object meant to store arbitrary state.

    It can be accessed using dot notation while exposing dict like functionalities.
    """

    __slots__ = ("_state", "_lock", "_frozen")

    _state: Dict[str, Any]
    _frozen: bool
    _lock: RLock

    def __init__(
        self, state: Optional[Union["State", Dict[str, Any], Iterable[Tuple[str, Any]]]] = None, frozen: bool = False
    ) -> None:
        """Initialize `State` with an optional value.

        Args:
             state: An optional string keyed dict for the initial state.
             frozen: Flag dictating whether the state object is frozen. No values can be deleted or set on a frozen state.

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

        if isinstance(state, State):
            state = state._state
        if not isinstance(state, dict) and isinstance(state, Iterable):
            state = dict(state)

        super().__setattr__("_state", state if state is not None else {})
        super().__setattr__("_frozen", frozen)
        super().__setattr__("_lock", RLock())

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
        if self._frozen:
            return self._state[key]

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
        if self._frozen:
            raise TypeError("State object is frozen. If you want to delete a value, you must unfreeze it first.")

        with self._lock:
            del self._state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an item in the state using subscription notation.

        Args:
            key: Key to set.
            value: Value to set.

        Returns:
            None
        """
        if self._frozen:
            raise TypeError("State object is frozen. If you want to set a value, you must unfreeze it first.")

        with self._lock:
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
        if self._frozen:
            raise TypeError("State object is frozen. If you want to set a value, you must unfreeze it first.")

        with self._lock:
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
        if self._frozen:
            raise TypeError("State object is frozen. If you want to delete a value, you must unfreeze it first.")

        try:
            with self._lock:
                del self._state[key]
        except KeyError as e:
            raise AttributeError(f"State instance has no attribute '{key}'") from e

    def __copy__(self) -> "State":
        """Return a shallow copy of the given state object.

        Customizes how the builtin "copy" function will work.
        """
        return self.__class__(copy(self._state), frozen=self._frozen)

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

    def freeze(self) -> None:
        """Set the state object to be frozen, preventing setting and deleting values.

        Returns:
            None.
        """
        self._frozen = True

    def unfreeze(self) -> None:
        """Set the state object to be unfrozen, allowing settings and deleting values.

        Returns:
            None
        """
        self._frozen = False
