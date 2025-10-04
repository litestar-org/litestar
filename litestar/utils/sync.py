from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Generator, Iterable
from typing import (
    TYPE_CHECKING,
    Callable,
    overload,
)

from typing_extensions import ParamSpec, TypeVar

from litestar.concurrency import sync_to_thread
from litestar.utils.predicates import is_async_callable

if TYPE_CHECKING:
    from types import TracebackType

__all__ = ("AsyncCallable", "AsyncIteratorWrapper", "ensure_async_callable", "is_async_callable")


P = ParamSpec("P")
T = TypeVar("T")
S = TypeVar("S", default=None)


def iterable_to_generator(iterator: Iterable[T]) -> Generator[T, S, None]:
    """Convert an iterable to a generator.

    Args:
        iterator: An iterable.

    Returns:
        A generator.
    """
    yield from iterator


@overload
def ensure_async_callable(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]: ...


@overload
def ensure_async_callable(fn: Callable[P, T]) -> Callable[P, Awaitable[T]]: ...


def ensure_async_callable(fn: Callable[P, T]) -> Callable[P, Awaitable[T]]:  # pyright: ignore
    """Ensure that ``fn`` is an asynchronous callable.
    If it is an asynchronous, return the original object, else wrap it in an
    ``AsyncCallable``
    """
    if is_async_callable(fn):
        return fn
    return AsyncCallable(fn)  # pyright: ignore


class AsyncCallable:
    """Wrap a given callable to be called in a thread pool using
    ``anyio.to_thread.run_sync``, keeping a reference to the original callable as
    :attr:`func`
    """

    def __init__(self, fn: Callable[P, T]) -> None:  # pyright: ignore
        self.func = fn

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:  # type: ignore[valid-type]
        return sync_to_thread(self.func, *args, **kwargs)  # type: ignore[arg-type]


class AsyncIteratorWrapper(AsyncGenerator[T, S]):
    """Asynchronous generator, wrapping an iterable or iterator."""

    __slots__ = ("_original_iterator", "generator", "iterator")

    def __init__(self, iterable: Iterable[T]) -> None:
        """Take a sync iterator or iterable and yields values from it asynchronously.

        Args:
            iterable: A sync iterable.
        """
        self._original_generator: Generator[T, S, None] = (
            iterable if isinstance(iterable, Generator) else iterable_to_generator(iterable)
        )

        self.iterator = iter(iterable)
        self.generator = self._async_generator()

    def _call_next(self) -> T:
        try:
            return next(self.iterator)
        except StopIteration as e:
            raise ValueError from e

    async def _async_generator(self) -> AsyncGenerator[T, None]:
        while True:
            try:
                yield await sync_to_thread(self._call_next)
            except ValueError:
                return

    def __aiter__(self) -> AsyncIteratorWrapper[T, S]:
        return self

    async def __anext__(self) -> T:
        return await self.generator.__anext__()

    async def aclose(self) -> None:
        self._original_generator.close()

    async def asend(self, value: S) -> T:
        return self._original_generator.send(value)

    async def athrow(
        self,
        typ: BaseException | type[BaseException],
        val: BaseException | object = None,
        tb: TracebackType | None = None,
    ) -> T:
        try:
            return (
                self._original_generator.throw(typ)
                if isinstance(typ, BaseException)
                else self._original_generator.throw(typ, val, tb)
            )
        except StopIteration as e:
            raise StopAsyncIteration from e
