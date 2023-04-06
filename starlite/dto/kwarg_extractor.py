from __future__ import annotations

from typing import TYPE_CHECKING

from .interface import DTOInterface

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine

    from starlite.connection import ASGIConnection, Request
    from starlite.types.parsed_signature import ParsedParameter

__all__ = ("create_dto_extractor",)


def create_dto_extractor(
    parsed_parameter: ParsedParameter, dto_type: type[DTOInterface]
) -> Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]:
    """Create a DTO data extractor.

    Args:
        parsed_parameter: :class:`ParsedParameter` instance representing the ``"data"`` kwarg.
        dto_type: The :class:`DTOInterface` subclass.

    Returns:
        An extractor function.
    """
    is_dto_annotated = parsed_parameter.parsed_type.is_subclass_of(DTOInterface)

    async def dto_extractor(connection: Request[Any, Any, Any]) -> Any:
        dto = await dto_type.from_connection(connection)
        if is_dto_annotated:
            return dto
        return dto.to_data_type()

    return dto_extractor  # type:ignore[return-value]
