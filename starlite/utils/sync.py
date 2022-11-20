from asyncio import iscoroutinefunction
from functools import partial
from inspect import getfullargspec, ismethod
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Iterator,
    List,
    TypeVar,
    Union,
)

from anyio.to_thread import run_sync
from typing_extensions import ParamSpec, TypeGuard

from starlite.utils.helpers import Ref

P = ParamSpec("P")
T = TypeVar("T")


def is_async_callable(value: Callable[P, T]) -> TypeGuard[Callable[P, Awaitable[T]]]:
    """Extend `asyncio.iscoroutinefunction()` to additionally detect async `partial` objects and class instances with
    `async def __call__()` defined.

    Args:
        value: Any

    Returns:
        Bool determining if type of `value` is an awaitable.
    """
    while isinstance(value, partial):
        value = value.func  # type: ignore[unreachable]

    return iscoroutinefunction(value) or (callable(value) and iscoroutinefunction(value.__call__))  # type: ignore[operator]


class AsyncCallable(Generic[P, T]):
    """Wrap a callable into an asynchronous callable."""

    __slots__ = ("args", "kwargs", "ref", "is_method", "num_expected_args")

    def __init__(self, fn: Callable[P, T]) -> None:
        """Initialize the wrapper from any callable.

        Args:
            fn: Callable to wrap - can be any sync or async callable.
        """
        self.is_method = ismethod(fn) or (callable(fn) and ismethod(fn.__call__))  # type: ignore
        self.num_expected_args = len(getfullargspec(fn).args) - (1 if self.is_method else 0)
        self.ref = Ref[Callable[..., Awaitable[T]]](
            fn if is_async_callable(fn) else async_partial(fn)  # pyright: ignore
        )

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Proxy the wrapped function's call method.

        Args:
            *args: Args of the wrapped function.
            **kwargs: Kwargs of the wrapper function.

        Returns:
            The return value of the wrapped function.
        """
        return await self.ref.value(*args, **kwargs)


def as_async_callable_list(value: Union[Callable, List[Callable]]) -> List[AsyncCallable]:
    """Wrap callables in `AsyncCallable`s.

    Args:
        value: A callable or list of callables.

    Returns:
        A list of AsyncCallable instances
    """
    if not isinstance(value, list):
        return [AsyncCallable(value)]
    return [AsyncCallable(v) for v in value]


def async_partial(fn: Callable) -> Callable:
    """Wrap a given sync function making it async.

    In difference to the 'asyncio.run_sync' function, it allows for passing kwargs.

    Args:
        fn: A sync callable to wrap.

    Returns:
        A wrapper
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        applied_kwarg = partial(fn, **kwargs)
        return await run_sync(applied_kwarg, *args)

    # this allows us to unwrap the partial later, so it's an important "hack".
    wrapper.func = fn  # type: ignore
    return wrapper


class AsyncIteratorWrapper(Generic[T]):
    """Asynchronous generator, wrapping an iterable or iterator."""

    __slots__ = ("iterator", "generator")

    def __init__(self, iterator: Union[Iterator[T], Iterable[T]]) -> None:
        """Take a sync iterator or iterable and yields values from it asynchronously.

        Args:
            iterator: A sync iterator or iterable.
        """
        self.iterator = iterator if isinstance(iterator, Iterator) else iter(iterator)
        self.generator = self._async_generator()

    def _call_next(self) -> T:
        try:
            return next(self.iterator)
        except StopIteration as e:
            raise ValueError from e

    async def _async_generator(self) -> AsyncGenerator[T, None]:
        while True:
            try:
                yield await run_sync(self._call_next)
            except ValueError:
                return

    def __aiter__(self) -> "AsyncIteratorWrapper[T]":
        return self

    async def __anext__(self) -> T:
        return await self.generator.__anext__()
