from inspect import Parameter, Signature
from typing import TYPE_CHECKING, Any, Optional, cast

from anyio import Lock

from starlite.types import Empty
from starlite.utils.sync import AsyncCallable, is_async_callable

if TYPE_CHECKING:
    from typing import Type

    from starlite.connection import Request
    from starlite.signature import SignatureModel
    from starlite.types import AnyCallable


def _wrap_cache_for_request(fn: "AnyCallable", override_name: Optional[str]) -> "AnyCallable":
    """Wrap the function to cache the result per request."""
    if override_name:
        key = override_name
    else:
        key = fn.__name__
    lock = Lock()
    wrapped_sig = sig = Signature.from_callable(fn)
    include_request = True
    if "request" not in sig.parameters:
        include_request = False
        params = list(sig.parameters.values())
        params.append(Parameter("request", Parameter.KEYWORD_ONLY, annotation="Request"))
        wrapped_sig = sig.replace(parameters=params)

    async def wrapped(*args: Any, request: "Request", **kwargs: Any) -> Any:
        async with lock:
            request_local_cache = request.state.setdefault("_dependency_cache", {})
            if key in request_local_cache:
                return request_local_cache[key]

            if include_request:
                kwargs["request"] = request

            if is_async_callable(fn):
                value = await fn(*args, **kwargs)
            else:
                value = fn(**kwargs)

            request_local_cache[key] = value
            return value

    wrapped.__name__ = fn.__name__
    wrapped.__signature__ = wrapped_sig  # type: ignore[attr-defined]
    return wrapped


class Provide:
    __slots__ = ("dependency", "use_cache", "value", "signature_model")

    def __init__(
        self,
        dependency: "AnyCallable",
        use_cache: bool = False,
        cache_per_request: bool = False,
        cache_key: Optional[str] = None,
        sync_to_thread: bool = False,
    ) -> None:
        """A wrapper class used for dependency injection.

        Args:
            dependency: Callable to inject, can be a function, method or class.
            use_cache: Cache the dependency return value. Defaults to False.
            cache_per_request: Cache the dependency return value per request. Defaults to False.
            cache_key: Override the key for per request caching. Defaults to the function name.
            sync_to_thread: Run sync code in an async thread. Defaults to False.
        """
        self.dependency = cast("AnyCallable", AsyncCallable(dependency) if sync_to_thread else dependency)
        if cache_per_request:
            self.dependency = _wrap_cache_for_request(self.dependency, cache_key)
        self.use_cache = use_cache
        self.value: Any = Empty
        self.signature_model: Optional["Type[SignatureModel]"] = None

    async def __call__(self, **kwargs: Any) -> Any:
        """Proxies call to 'self.proxy'."""

        if self.use_cache and self.value is not Empty:
            return self.value

        if is_async_callable(self.dependency):
            value = await self.dependency(**kwargs)
        else:
            value = self.dependency(**kwargs)

        if self.use_cache:
            self.value = value

        return value

    def __eq__(self, other: Any) -> bool:
        # check if memory address is identical, otherwise compare attributes
        return other is self or (
            isinstance(other, self.__class__)
            and other.dependency == self.dependency
            and other.use_cache == self.use_cache
            and other.value == self.value
        )
