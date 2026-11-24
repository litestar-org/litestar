"""Name the field msgspec rejects in a model a DTO transfers."""

from typing import TYPE_CHECKING, Any, Final

import msgspec

from litestar.dto._types import (
    CollectionType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TransferDTOFieldDefinition,
    TransferType,
    TupleType,
    UnionType,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from msgspec import Struct

    from litestar.typing import FieldDefinition

__all__ = (
    "CONSTRAINT_HINT",
    "contains_meta",
    "find_rejected_field",
    "qualified_name",
    "rejected_field_message",
    "rejection_hint",
)

CONSTRAINT_HINT: Final = (
    "attach the constraint to the member type it applies to, e.g. Optional[Annotated[str, Meta(...)]]"
)
_UNION_HINT: Final = "tag the union members or decode the body yourself"


def qualified_name(value: Any) -> str:
    """Return the module-qualified name of the class ``value``."""
    return f"{value.__module__}.{value.__qualname__}"


def rejected_field_message(
    prefix: str,
    model: Any,
    field_definition: "FieldDefinition",
    exc: Exception,
    *,
    owner: Any = None,
    hint: str | None = None,
) -> str:
    """Return the message saying that msgspec rejects ``field_definition`` of ``model``, or of ``owner`` if the field
    belongs to a model nested in ``model``, raising ``exc``.
    """
    of_owner = f" of {qualified_name(owner)!r}" if owner is not None else ""
    reason = str(exc).split(" - type `", 1)[0]
    return (
        f"{prefix} {qualified_name(model)!r}: field {field_definition.name!r}{of_owner}, annotated "
        f"{field_definition.raw!r}, is rejected by msgspec ({reason}){f'; {hint}' if hint else ''}"
    )


def contains_meta(field_definition: "FieldDefinition") -> bool:
    """Return whether ``field_definition`` or one of its inner types carries a ``msgspec.Meta``."""
    return any(isinstance(m, msgspec.Meta) for m in field_definition.metadata) or any(
        contains_meta(inner_type) for inner_type in field_definition.inner_types
    )


def _iter_nested_field_infos(transfer_type: TransferType) -> "Iterator[tuple[Any, NestedFieldInfo]]":
    if isinstance(transfer_type, SimpleType):
        if transfer_type.nested_field_info:
            yield transfer_type.field_definition.annotation, transfer_type.nested_field_info
    elif isinstance(transfer_type, CollectionType):
        yield from _iter_nested_field_infos(transfer_type.inner_type)
    elif isinstance(transfer_type, MappingType):
        yield from _iter_nested_field_infos(transfer_type.key_type)
        yield from _iter_nested_field_infos(transfer_type.value_type)
    elif isinstance(transfer_type, (TupleType, UnionType)):
        for inner_type in transfer_type.inner_types:
            yield from _iter_nested_field_infos(inner_type)


def find_rejected_field(
    owner: Any, field_definitions: tuple[TransferDTOFieldDefinition, ...], transfer_model: "type[Struct]"
) -> tuple[Any, TransferDTOFieldDefinition, TypeError] | None:
    """Return the innermost field of ``transfer_model`` msgspec cannot decode, with the model owning it and the
    error, or ``None`` if msgspec decodes every field.
    """
    field_types = {f.name: f.type for f in msgspec.structs.fields(transfer_model)}
    for field_definition in field_definitions:
        if field_definition.is_excluded:
            continue
        try:
            msgspec.json.Decoder(field_types[field_definition.name], strict=False)
        except TypeError as exc:
            for nested_owner, nested_field_info in _iter_nested_field_infos(field_definition.transfer_type):
                if found := find_rejected_field(
                    nested_owner, nested_field_info.field_definitions, nested_field_info.model
                ):
                    return found
            return owner, field_definition, exc
    return None


def rejection_hint(field_definition: TransferDTOFieldDefinition) -> str | None:
    """Return how to make msgspec accept ``field_definition``, if there is a known way."""
    transfer_type = field_definition.transfer_type
    if (
        isinstance(transfer_type, UnionType)
        and sum(isinstance(t, SimpleType) and t.nested_field_info is not None for t in transfer_type.inner_types) > 1
    ):
        return _UNION_HINT
    return CONSTRAINT_HINT if contains_meta(field_definition) else None
