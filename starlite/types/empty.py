from __future__ import annotations

from typing import Type

__all__ = ("Empty", "EmptyType")


class Empty:
    """A sentinel class used as placeholder."""


EmptyType = Type[Empty]
