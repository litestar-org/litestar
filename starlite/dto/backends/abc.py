"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
and back again, to bytes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from starlite.dto.types import FieldDefinitionsType
    from starlite.enums import MediaType

__all__ = ("AbstractDTOBackend",)


class AbstractDTOBackend(ABC):
    @classmethod
    @abstractmethod
    def from_field_definitions(cls, field_definitions: FieldDefinitionsType) -> Any:
        ...

    @abstractmethod
    def raw_to_dict(self, raw: bytes, media_type: MediaType | str) -> dict[str, Any]:
        ...
