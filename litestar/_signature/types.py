from __future__ import annotations

from typing import Any

from msgspec import ValidationError

__all__ = ("ExtendedMsgSpecValidationError",)


class ExtendedMsgSpecValidationError(ValidationError):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(errors)
