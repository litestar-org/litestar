"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
and back again, to bytes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

__all__ = ("AbstractDTOBackend",)


if TYPE_CHECKING:
    from typing import Any


class AbstractDTOBackend(ABC):
    @abstractmethod
    def receive_fields(self) -> Any:
        ...
