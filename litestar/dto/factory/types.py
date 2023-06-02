from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Literal

from litestar.utils.signature import ParsedParameter

if TYPE_CHECKING:
    from typing import Any

    from typing_extensions import TypeAlias

    from litestar.dto.types import ForType

    from .field import DTOField

__all__ = ("FieldDefinition", "RenameStrategy")


@dataclass(frozen=True)
class FieldDefinition(ParsedParameter):
    """A model field representation for purposes of generating a DTO backend model type."""

    __slots__ = (
        "default_factory",
        "dto_field",
        "dto_for",
        "unique_model_name",
    )

    unique_model_name: str
    """Unique identifier of model that owns the field."""
    default_factory: Callable[[], Any] | None
    """Default factory of the field."""
    dto_field: DTOField | None
    """DTO field configuration."""
    dto_for: ForType | None
    """Direction of transfer for field.

    Specify if the field definition should only be added to models for only the request (``"data"``) or response
    (``"return"``). If there should be no such distinction, set to ``None``.

    This is to support special cases where the type to set an attribute may be different to the type received when
    retrieving its value. For example, a :class:`sqlalchemy.ext.hybrid.hybrid_property` may be set with a ``str`` but
    retrieved as some other type.

    The difference between this, and marking a field as read-only or private, is that it cannot be overridden by the end
    user.
    """

    def unique_name(self) -> str:
        return f"{self.unique_model_name}.{self.name}"


RenameStrategy: TypeAlias = 'Literal["lower", "upper", "camel", "pascal"] | Callable[[str], str]'
"""A pre-defined strategy or a custom callback for converting DTO field names."""
