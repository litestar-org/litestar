from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, TypeVar

from starlite.types import Empty, EmptyType

__all__ = ("async_next", "py_39_safe_annotations")


if TYPE_CHECKING:
    from typing import Any, AsyncGenerator, Generator

T = TypeVar("T")
D = TypeVar("D")

try:
    async_next = anext  # pyright: ignore
except NameError:  # pragma: no cover

    async def async_next(gen: AsyncGenerator[T, Any], default: D | EmptyType = Empty) -> T | D:  # type: ignore[misc]
        """Backwards compatibility shim for Python<3.10."""
        try:
            return await gen.__anext__()
        except StopAsyncIteration as exc:
            if default is not Empty:
                return default  # type: ignore[return-value]
            raise exc


@contextmanager
def py_39_safe_annotations(annotated: Any) -> Generator[Any, None, None]:
    """Ensure annotations are backward compatible with Python 3.9 and lower.

    If detected python version is <= 3.9, converts forward referenced annotations like `"A | B"` into `"Union[A, B]"`.

    On exit of the context manager, the original annotations are replaced.

    Args:
        annotated: something that has `__annotations__` attribute.

    Yields:
        ``annotated`` with patched `__annotations__` attribute if on python < 3.10.
    """
    if sys.version_info < (3, 10) and hasattr(annotated, "__annotations__"):
        orig_annotations = annotated.__annotations__
        new_annotations = dict(orig_annotations)
        for k, v in orig_annotations.items():
            if isinstance(v, str) and "|" in v:
                new_annotations[k] = f"Union[{','.join(map(str.strip, v.split('|')))}]"
        annotated.__annotations__ = new_annotations
        yield
        annotated.__annotations__ = orig_annotations
    else:
        yield
