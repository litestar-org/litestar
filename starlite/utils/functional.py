from typing import Any, Callable, Dict, Generic, Literal, TypeVar, Union, cast

from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


class FunctionWrapper(Generic[P, T]):
    def __init__(self, fn: Callable[P, T]):
        """
        Takes a callable, if it's a method - preserves its 'self' argument, otherwise wraps it in 'staticmethod'.
        Args:
            fn: A callable to wrap.
        """
        self.self_ref: Any = None
        self.fn: Union[Dict[Literal["wrapped"], Callable], Callable]
        if hasattr(fn, "__self__"):
            self.fn = {"wrapped": fn}
        else:
            self.fn = staticmethod(fn)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """A proxy to the wrapped function's call method.

        Args:
            *args: Args of the wrapped function.
            **kwargs: Kwargs of the wrapper function.

        Returns:
            The return value of the wrapped function.
        """
        if isinstance(self.fn, dict):
            return cast("T", self.fn["wrapped"](*args, **kwargs))
        return cast("T", self.fn(*args, **kwargs))
