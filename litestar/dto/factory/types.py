from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Literal

from litestar.types.empty import Empty
from litestar.utils.dataclass import simple_asdict
from litestar.utils.signature import ParsedParameter

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from typing_extensions import TypeAlias

    from litestar.types import EmptyType

    from .field import DTOField

__all__ = ("FieldDefinition", "FieldDefinitionsType", "NestedFieldDefinition")


@dataclass(frozen=True)
class FieldDefinition(ParsedParameter):
    """A model field representation for purposes of generating a DTO backend model type."""

    default_factory: Callable[[], Any] | EmptyType = field(default=Empty)
    """Default factory of the field."""
    dto_field: DTOField | None = field(default=None)
    """DTO field configuration."""
    serialization_name: str | None = field(default=None)

    def copy_with(self, **kwargs: Any) -> FieldDefinition:
        """Copy the field definition with the given keyword arguments.

        Args:
            **kwargs: Keyword arguments to update the field definition with.

        Returns:
            Updated field definition.
        """
        return FieldDefinition(**{**simple_asdict(self, convert_nested=False), **kwargs})


@dataclass
class NestedFieldDefinition:
    """For representing nested model."""

    field_definition: FieldDefinition
    nested_type: Any
    nested_field_definitions: FieldDefinitionsType = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Name of the field."""
        return self.field_definition.name

    @property
    def serialization_name(self) -> str | None:
        """Serialization name of the field."""
        return self.field_definition.serialization_name

    def make_field_type(self, inner_type: type) -> Any:
        if self.field_definition.parsed_type.is_collection:
            return self.field_definition.parsed_type.safe_generic_origin[inner_type]
        if self.field_definition.parsed_type.is_optional:
            return self.field_definition.parsed_type.safe_generic_origin[inner_type, None]
        return inner_type


FieldDefinitionsType: TypeAlias = "Mapping[str, FieldDefinition | NestedFieldDefinition]"
"""Generic representation of names and types."""

RenameStrategy: TypeAlias = 'Literal["lower", "upper", "camel", "pascal"] | Callable[[str], str]'
"""A pre-defined strategy or a custom callback for converting DTO field names."""
