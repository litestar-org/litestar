from typing import TYPE_CHECKING, Any, Optional, cast

from anyio import Lock

from starlite.types import Empty
from starlite.utils.sync import AsyncCallable, is_async_callable

if TYPE_CHECKING:
    from typing import Type

    from starlite.signature import SignatureModel
    from starlite.types import AnyCallable


class Provide:
    __slots__ = ("dependency", "use_cache", "cache_per_request", "cache_key", "lock", "value", "signature_model")

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
        self.use_cache = use_cache
        self.cache_per_request = cache_per_request
        self.cache_key = cache_key if cache_key else getattr(dependency, "__name__", "anonymous")
        self.lock = Lock()
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
