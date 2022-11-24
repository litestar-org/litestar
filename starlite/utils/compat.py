from typing import Any, AsyncGenerator, TypeVar, cast, Union

from starlite.types import Empty

T = TypeVar("T")
D = TypeVar("D")

try:
    async_next = anext
except NameError:

    async def async_next(gen: AsyncGenerator[T, Any], default: D = Empty) -> Union[T, D]:
        try:
            return await gen.__anext__()
        except StopAsyncIteration as exc:
            if default is not Empty:
                return default
            raise exc
