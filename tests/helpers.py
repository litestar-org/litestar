from __future__ import annotations

import inspect
import random
import sys
from contextlib import AbstractContextManager
from typing import Any, AsyncContextManager, Awaitable, ContextManager, TypeVar, cast, overload

T = TypeVar("T")


RANDOM = random.Random(b"bA\xcd\x00\xa9$\xa7\x17\x1c\x10")


# TODO: Remove when dropping 3.9
if sys.version_info < (3, 9):

    def randbytes(n: int) -> bytes:
        return bytearray(RANDOM.getrandbits(8) for _ in range(n))

else:
    randbytes = RANDOM.randbytes


@overload
async def maybe_async(obj: Awaitable[T]) -> T:
    ...


@overload
async def maybe_async(obj: T) -> T:
    ...


async def maybe_async(obj: Awaitable[T] | T) -> T:
    return cast(T, await obj) if inspect.isawaitable(obj) else cast(T, obj)


class _AsyncContextManagerWrapper(AsyncContextManager):
    def __init__(self, cm: AbstractContextManager):
        self.cm = cm

    async def __aenter__(self) -> Any:
        return self.cm.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        return self.cm.__exit__(exc_type, exc_val, exc_tb)


def maybe_async_cm(obj: ContextManager[T] | AsyncContextManager[T]) -> AsyncContextManager[T]:
    if isinstance(obj, AbstractContextManager):
        return cast(AsyncContextManager[T], _AsyncContextManagerWrapper(obj))
    return obj
