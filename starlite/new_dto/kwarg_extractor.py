from __future__ import annotations

from typing import TYPE_CHECKING, cast

from typing_extensions import get_args

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine

    from starlite.connection import ASGIConnection, Request
    from starlite.signature.models import SignatureField

    from .abc import AbstractDTO


def create_dto_extractor(
    signature_field: SignatureField,
) -> Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]:
    """Create a DTO data extractor.

    Args:
        signature_field: A SignatureField instance.

    Returns:
        An extractor function.
    """
    if signature_field.is_non_string_iterable:
        # what about fixed sized, heterogeneous tuples?
        dto_type = cast("type[AbstractDTO[Any]]", get_args(signature_field.field_type)[0])

        async def collection_dto_extractor(connection: Request[Any, Any, Any]) -> list[AbstractDTO[Any]]:
            return dto_type.list_from_bytes(await connection.body())

        return collection_dto_extractor  # type:ignore[return-value]

    dto_type = cast("type[AbstractDTO[Any]]", signature_field.field_type)

    async def scalar_dto_extractor(connection: Request[Any, Any, Any]) -> AbstractDTO[Any]:
        return dto_type.from_bytes(await connection.body())

    return scalar_dto_extractor  # type:ignore[return-value]
