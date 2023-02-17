from typing import Awaitable, List, Literal, TypeVar, Union

T = TypeVar("T")

SyncOrAsyncUnion = Union[T, Awaitable[T]]
"""Types 'T' as a union of T and awaitable T."""
SingleOrList = Union[T, List[T]]
"""Types 'T' as a single value or a list T."""
AnyIOBackend = Literal["asyncio", "trio"]
"""Anyio backend names."""
