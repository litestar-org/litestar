from typing import TYPE_CHECKING, Any

from starlite.types import Empty
from starlite.utils.helpers import Ref
from starlite.utils.sync import is_async_callable

if TYPE_CHECKING:
    from typing import Type

    from starlite.signature import SignatureModel
    from starlite.types import AnyCallable


class Provide:
    """A wrapper class for dependency injection."""

    __slots__ = (
        "dependency",
        "use_cache",
        "lock",
        "value",
        "signature_model",
        "sync_to_thread",
        "has_sync_callable",
    )

    signature_model: "Type[SignatureModel]"

    def __init__(
        self,
        dependency: "AnyCallable",
        use_cache: bool = False,
        sync_to_thread: bool = False,
    ) -> None:
        """Initialize `Provide`

        Args:
            dependency: Callable to inject, can be a function, method or class.
            use_cache: Cache the dependency return value. Defaults to False.
            sync_to_thread: Run sync code in an async thread. Defaults to False.
        """
        self.sync_to_thread = sync_to_thread
        self.dependency = Ref["AnyCallable"](dependency)
        self.use_cache = use_cache
        self.value: Any = Empty
        self.has_sync_callable = not is_async_callable(self.dependency.value)

    async def __call__(self, **kwargs: Any) -> Any:
        """Proxy a call to 'self.proxy'."""

        if self.use_cache and self.value is not Empty:
            return self.value

        if self.has_sync_callable:
            value = self.dependency.value(**kwargs)
        else:
            value = await self.dependency.value(**kwargs)

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
