from __future__ import annotations

import inspect
import random
import sys
from contextlib import AbstractContextManager
from typing import AsyncContextManager, Awaitable, ContextManager, TypeVar, cast, overload

from anyio._core._compat import _ContextManagerWrapper

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


def maybe_async_cm(obj: ContextManager[T] | AsyncContextManager[T]) -> AsyncContextManager[T]:
    if isinstance(obj, AbstractContextManager):
        return cast(AsyncContextManager[T], _ContextManagerWrapper(obj))
    return obj
