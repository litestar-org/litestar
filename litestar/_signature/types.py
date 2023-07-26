from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from msgspec import ValidationError


class ExtendedMsgSpecValidationError(ValidationError):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(errors)


@dataclass(frozen=True)
class SerializationWrapper:
    __slots__ = ("wrapped_type",)

    wrapped_type: Any
