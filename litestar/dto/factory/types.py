from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Callable, Literal

from litestar.utils.signature import ParsedParameter

if TYPE_CHECKING:
    from typing import Any

    from typing_extensions import TypeAlias

    from .field import DTOField

__all__ = ("FieldDefinition", "RenameStrategy")


@dataclass(frozen=True)
class FieldDefinition(ParsedParameter):
    """A model field representation for purposes of generating a DTO backend model type."""

    model_fqdn: str
    """Unique identifier of model that owns the field."""
    default_factory: Callable[[], Any] | None
    """Default factory of the field."""
    dto_field: DTOField | None
    """DTO field configuration."""

    @cached_property
    def unique_name(self) -> str:
        return f"{self.model_fqdn}.{self.name}"


RenameStrategy: TypeAlias = 'Literal["lower", "upper", "camel", "pascal"] | Callable[[str], str]'
"""A pre-defined strategy or a custom callback for converting DTO field names."""
