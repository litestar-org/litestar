from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Iterable, Iterator, Sequence
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeVar,
    Union,
)

from typing_extensions import TypeAliasType

if TYPE_CHECKING:
    from litestar.response.sse import ServerSentEventMessage


T = TypeVar("T")

__all__ = ("AnyIOBackend", "MaybePartial", "OptionalSequence", "SSEData", "StreamType", "SyncOrAsyncUnion")

OptionalSequence = TypeAliasType("OptionalSequence", Sequence[T] | None, type_params=(T,))
"""Types 'T' as union of Sequence[T] and None."""

SyncOrAsyncUnion = TypeAliasType("SyncOrAsyncUnion", Union[T, Awaitable[T]], type_params=(T,))
"""Types 'T' as a union of T and awaitable T."""


AnyIOBackend = TypeAliasType("AnyIOBackend", Literal["asyncio", "trio"])
"""Anyio backend names."""

StreamType = TypeAliasType(
    "StreamType", Union[Iterable[T], Iterator[T], AsyncIterable[T], AsyncIterator[T]], type_params=(T,)
)
"""A stream type."""

MaybePartial = TypeAliasType("MaybePartial", Union[T, partial], type_params=(T,))
"""A potentially partial callable."""

SSEData = TypeAliasType("SSEData", Union[int, str, bytes, dict[str, Any], "ServerSentEventMessage"])
"""A type alias for SSE data."""
