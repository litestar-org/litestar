from typing import Any, Callable, Dict, Generic, TypeVar, cast

from typing_extensions import Literal, ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


class CallableWrapper(Generic[P, T]):
    def __init__(self, fn: Callable[P, T]):
        """
        Takes a callable, if it's a method - preserves its 'self' argument, otherwise wraps it in 'staticmethod'.
        Args:
            fn: A callable to wrap.
        """
        self.self_ref: Any = None
        self.wrapper: Dict[Literal["fn"], Callable] = {"fn": fn}

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """A proxy to the wrapped function's call method.

        Args:
            *args: Args of the wrapped function.
            **kwargs: Kwargs of the wrapper function.

        Returns:
            The return value of the wrapped function.
        """
        fn = self.wrapper["fn"]
        return cast("T", fn(*args, **kwargs))
