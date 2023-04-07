from __future__ import annotations

from inspect import isclass
from typing import TYPE_CHECKING, Any

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty
from litestar.utils import Ref, is_async_callable

__all__ = ("Provide",)


if TYPE_CHECKING:
    from litestar._signature import SignatureModel
    from litestar.types import AnyCallable


class Provide:
    """Wrapper class for dependency injection"""

    __slots__ = (
        "dependency",
        "has_sync_callable",
        "has_class_dependency",
        "signature_model",
        "sync_to_thread",
        "use_cache",
        "value",
    )

    signature_model: type[SignatureModel]
    dependency: Ref[AnyCallable]

    def __init__(
        self,
        dependency: AnyCallable | type,
        use_cache: bool = False,
        sync_to_thread: bool = False,
    ) -> None:
        """Initialize ``Provide``

        Args:
            dependency: Callable to call or class to instantiate. The result is then injected as a dependency.
            use_cache: Cache the dependency return value. Defaults to False.
            sync_to_thread: Run sync code in an async thread. Defaults to False.
        """
        if not callable(dependency):
            raise ImproperlyConfiguredException("Provider dependency must a callable value")

        self.dependency = Ref["AnyCallable"](dependency)
        self.has_sync_callable = isclass(dependency) or not is_async_callable(dependency)
        self.sync_to_thread = sync_to_thread
        self.use_cache = use_cache
        self.value: Any = Empty

    async def __call__(self, **kwargs: Any) -> Any:
        """Call the provider's dependency."""

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
