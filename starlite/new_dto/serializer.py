from __future__ import annotations

from collections.abc import Iterable as CollectionsIterable
from contextlib import suppress
from typing import TYPE_CHECKING

from . import AbstractDTO

__all__ = ("serialize_dto_for_media_type",)


if TYPE_CHECKING:
    from typing import Iterable

    from starlite.enums import MediaType


def serialize_dto_for_media_type(
    media_type: MediaType | str, dto_data: AbstractDTO | Iterable[AbstractDTO]
) -> bytes | None:
    """Create a bytes representation of the dto data.
    Args:
        dto_data: instance or iterable of DTO instances
        media_type: serialization format

    Returns:
        ``bytes`` if the data is serializable as DTO data, else ``None``.
    """
    data: bytes | None = None
    if isinstance(dto_data, AbstractDTO):
        return dto_data.to_bytes(media_type=media_type)

    if isinstance(dto_data, CollectionsIterable):
        with suppress(StopIteration):
            first_item = next(iter(dto_data))

            if isinstance(first_item, AbstractDTO):
                return first_item.encode_iterable(dto_data, media_type=media_type)
    return data
