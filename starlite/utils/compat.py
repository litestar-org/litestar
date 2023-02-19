from __future__ import annotations

from sys import version_info
from typing import Any, AsyncGenerator, Callable, TypeVar

from starlite.types import Empty, EmptyType

T = TypeVar("T")
D = TypeVar("D")

try:
    async_next = anext  # pyright: ignore
except NameError:  # pragma: no cover

    async def async_next(gen: AsyncGenerator[T, Any], default: D | EmptyType = Empty) -> T | D:  # type: ignore[misc]
        """Backwards compatibility shim for Python<3.10."""
        try:
            return await gen.__anext__()  # pylint: disable=C2801
        except StopAsyncIteration as exc:
            if default is not Empty:
                return default  # type: ignore[return-value]
            raise exc


C = TypeVar("C", bound=Callable)


def validate_arguments(fn: C) -> C:
    """Proxy pydantic `validate_arguments` decorator to ignore python 3.8, which doesn't support future
    annotations.

    :param fn: A callable to decorate.
    :return: Either the decorated callable, if python version is 3.8, or the callable itself.
    """
    if version_info < (3, 9):  # pragma: no cover
        return fn

    from pydantic import validate_arguments as pydantic_validate_arguments

    return pydantic_validate_arguments(
        config={"arbitrary_types_allowed": True, "copy_on_model_validation": "none", "globalns": {"Callable": Callable}}
    )(fn)
