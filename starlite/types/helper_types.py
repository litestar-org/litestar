from typing import Awaitable, Literal, Optional, Sequence, TypeVar, Union

T = TypeVar("T")

OptionalSequence = Optional[Sequence[T]]
"""Types 'T' as union of Sequence[T] and None."""
SyncOrAsyncUnion = Union[T, Awaitable[T]]
"""Types 'T' as a union of T and awaitable T."""
AnyIOBackend = Literal["asyncio", "trio"]
"""Anyio backend names."""
