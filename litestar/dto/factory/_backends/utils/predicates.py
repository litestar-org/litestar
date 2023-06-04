from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.dto.factory import Mark

if TYPE_CHECKING:
    from typing import AbstractSet

    from litestar.dto.factory._backends.types import TransferFieldDefinition
    from litestar.dto.factory.data_structures import FieldDefinition
    from litestar.dto.types import ForType

__all__ = (
    "should_exclude_field",
    "should_ignore_field",
    "should_mark_private",
    "should_skip_transfer",
)


def should_exclude_field(field_definition: FieldDefinition, exclude: AbstractSet[str], dto_for: ForType) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    Args:
        field_definition: defined DTO field
        exclude: names of fields to exclude
        dto_for: indicates whether the DTO is for the request body or response.

    Returns:
        ``True`` if the field should not be included in any data transfer.
    """
    field_name = field_definition.name
    dto_field = field_definition.dto_field
    excluded = field_name in exclude
    private = dto_field and dto_field.mark is Mark.PRIVATE
    read_only_for_data = dto_for == "data" and dto_field and dto_field.mark is Mark.READ_ONLY
    write_only_for_return = dto_for == "return" and dto_field and dto_field.mark is Mark.WRITE_ONLY
    return bool(excluded or private or read_only_for_data or write_only_for_return)


def should_ignore_field(field_definition: FieldDefinition, dto_for: ForType) -> bool:
    """Returns ``True`` where a field should be ignored.

    An ignored field is different to an excluded one in that we do not produce a
    ``TransferFieldDefinition`` for it at all.

    This allows ``AbstractDTOFactory`` concrete types to generate multiple field definitions
    for the same field name, each for a different transfer direction.

    One example of this is the :class:`sqlalchemy.ext.hybrid.hybrid_property` which, might have
    a different type accepted by its setter method, than is returned by its getter method.
    """
    return field_definition.dto_for is not None and field_definition.dto_for != dto_for


def should_mark_private(field_definition: FieldDefinition, underscore_fields_private: bool) -> bool:
    """Returns ``True`` where a field should be marked as private.

    Fields should be marked as private when:
    - the ``underscore_fields_private`` flag is set.
    - the field is not already marked.
    - the field name is prefixed with an underscore

    Args:
        field_definition: defined DTO field
        underscore_fields_private: whether fields prefixed with an underscore should be marked as private.
    """
    return (
        underscore_fields_private and field_definition.dto_field.mark is None and field_definition.name.startswith("_")
    )


def should_skip_transfer(
    dto_for: ForType,
    field_definition: TransferFieldDefinition,
    source_has_value: bool,
) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    We should skip transfer when:
    - the field is excluded and the DTO is for the return data.
    - the DTO is for request data, and the field is not in the source instance.

    Args:
        dto_for: indicates whether the DTO is for the request body or response.
        field_definition: model field definition.
        source_has_value: indicates whether the source instance has a value for the field.
    """
    return (dto_for == "return" and field_definition.is_excluded) or (dto_for == "data" and not source_has_value)
