from copy import copy

from starlette.datastructures import State as StarletteStateClass


class State(StarletteStateClass):
    def __copy__(self) -> "State":
        """
        Returns a shallow copy of the given state object.
        Customizes how the builtin "copy" function will work.
        """
        return self.__class__(copy(self._state))

    def copy(self) -> "State":
        """Returns a shallow copy of the given state object"""
        return copy(self)
