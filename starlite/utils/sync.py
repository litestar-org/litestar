from functools import partial
from inspect import getfullargspec, ismethod
from typing import Any, Callable, Dict, Generic, List, TypeVar, Union, cast

from anyio.to_thread import run_sync
from typing_extensions import Literal, ParamSpec

from starlite.utils.predicates import is_async_callable

P = ParamSpec("P")
T = TypeVar("T")


class AsyncCallable(Generic[P, T]):
    __slots__ = ("args", "kwargs", "wrapped_callable", "is_method", "num_expected_args")

    def __init__(self, fn: Callable[P, T]) -> None:
        """Utility class that wraps a callable and ensures it can be called as
        an async function.

        Args:
            fn: Callable to wrap - can be any sync or async callable.
        """

        self.is_method = ismethod(fn)
        self.num_expected_args = len(getfullargspec(fn).args) - (1 if self.is_method else 0)
        self.wrapped_callable: Dict[Literal["fn"], Callable] = {
            "fn": fn if is_async_callable(fn) else async_partial(fn)
        }

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """A proxy to the wrapped function's call method.

        Args:
            *args: Args of the wrapped function.
            **kwargs: Kwargs of the wrapper function.

        Returns:
            The return value of the wrapped function.
        """
        return cast("T", await self.wrapped_callable["fn"](*args, **kwargs))


def as_async_callable_list(value: Union[Callable, List[Callable]]) -> List[AsyncCallable]:
    """
    Helper function to handle wrapping values in AsyncCallables
    Args:
        value: A callable or list of callables.

    Returns:
        A list of AsyncCallable instances
    """
    if not isinstance(value, list):
        return [AsyncCallable(value)]
    return [AsyncCallable(v) for v in value]


def async_partial(fn: Callable) -> Callable:
    """This function wraps a given sync function making it async. In difference
    to the 'asyncio.run_sync' function, it allows for passing kwargs.

    Args:
        fn: A sync callable to wrap.

    Returns:
        A wrapper
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        applied_kwarg = partial(fn, **kwargs)
        return await run_sync(applied_kwarg, *args)

    return wrapper
