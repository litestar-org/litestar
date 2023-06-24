from __future__ import annotations

from functools import partial
from typing import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Iterable,
    Iterator,
    Literal,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

T = TypeVar("T")

__all__ = ("OptionalSequence", "SyncOrAsyncUnion", "AnyIOBackend", "StreamType", "MaybePartial")

OptionalSequence = Optional[Sequence[T]]
"""Types 'T' as union of Sequence[T] and None."""

SyncOrAsyncUnion = Union[T, Awaitable[T]]
"""Types 'T' as a union of T and awaitable T."""


AnyIOBackend = Literal["asyncio", "trio"]
"""Anyio backend names."""

StreamType = Union[Iterable[T], Iterator[T], AsyncIterable[T], AsyncIterator[T]]
"""A stream type."""

MaybePartial = Union[T, partial]
"""A potentially partial callable."""
