from typing import Any


class DeprecatedProperty:
    def __get__(self, instance: Any, owner: Any) -> None:
        raise AttributeError
