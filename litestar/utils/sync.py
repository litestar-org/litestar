from __future__ import annotations

from functools import partial
from inspect import getfullargspec, ismethod
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Iterator,
    TypeVar,
    cast,
)

from anyio.to_thread import run_sync
from typing_extensions import ParamSpec

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty
from litestar.utils.helpers import Ref, unwrap_partial
from litestar.utils.predicates import is_async_callable

if TYPE_CHECKING:
    from litestar.types.empty import EmptyType
    from litestar.utils.signature import ParsedSignature

__all__ = ("AsyncCallable", "AsyncIteratorWrapper", "async_partial", "is_async_callable")


P = ParamSpec("P")
T = TypeVar("T")


class AsyncCallable(Generic[P, T]):
    """Wrap a callable into an asynchronous callable."""

    __slots__ = ("args", "kwargs", "ref", "is_method", "num_expected_args", "_parsed_signature")

    def __init__(self, fn: Callable[P, T]) -> None:
        """Initialize the wrapper from any callable.

        Args:
            fn: Callable to wrap - can be any sync or async callable.
        """
        self._parsed_signature: ParsedSignature | EmptyType = Empty
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

    @property
    def parsed_signature(self) -> ParsedSignature:
        if self._parsed_signature is Empty:
            raise ImproperlyConfiguredException(
                "Parsed signature is not set. Call `set_parsed_signature()` at an appropriate time during handler"
                "registration."
            )
        return cast("ParsedSignature", self._parsed_signature)

    def set_parsed_signature(self, namespace: dict[str, Any]) -> None:
        """Set the parsed signature of the wrapped function.

        Args:
            namespace: Namespace for forward ref resolution.
        """
        from litestar.utils.signature import ParsedSignature

        self._parsed_signature = ParsedSignature.from_fn(unwrap_partial(self.ref.value), namespace)


def async_partial(fn: Callable) -> Callable:
    """Wrap a given sync function making it async.

    In difference to the :func:`asyncio.run_sync` function, it allows for passing kwargs.

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

    def __init__(self, iterator: Iterator[T] | Iterable[T]) -> None:
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

    def __aiter__(self) -> AsyncIteratorWrapper[T]:
        return self

    async def __anext__(self) -> T:
        return await self.generator.__anext__()
