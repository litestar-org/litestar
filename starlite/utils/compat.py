from typing import Any, AsyncGenerator, TypeVar, Union

from starlite.types import Empty, EmptyType

T = TypeVar("T")
D = TypeVar("D")

try:
    async_next = anext  # pyright: ignore
except NameError:

    async def async_next(gen: AsyncGenerator[T, Any], default: Union[D, EmptyType] = Empty) -> Union[T, D]:  # type: ignore[misc]
        """Backwards compatibility shim for Python<3.10."""
        try:
            return await gen.__anext__()  # pylint: disable=C2801
        except StopAsyncIteration as exc:
            if default is not Empty:
                return default  # type: ignore[return-value]
            raise exc
