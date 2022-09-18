from typing import Awaitable, List, TypeVar, Union

T = TypeVar("T")

SyncOrAsyncUnion = Union[T, Awaitable[T]]
SingleOrList = Union[T, List[T]]
