from __future__ import annotations

from inspect import isclass
from typing import TYPE_CHECKING, Any

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty
from litestar.utils import Ref, async_partial
from litestar.utils.predicates import is_async_callable, is_sync_or_async_generator
from litestar.utils.warnings import (
    warn_implicit_sync_to_thread,
    warn_sync_to_thread_with_async_callable,
    warn_sync_to_thread_with_generator,
)

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
        sync_to_thread: bool | None = None,
    ) -> None:
        """Initialize ``Provide``

        Args:
            dependency: Callable to call or class to instantiate. The result is then injected as a dependency.
            use_cache: Cache the dependency return value. Defaults to False.
            sync_to_thread: Run sync code in an async thread. Defaults to False.
        """
        if not callable(dependency):
            raise ImproperlyConfiguredException("Provider dependency must a callable value")

        has_sync_callable = isclass(dependency) or not is_async_callable(dependency)

        if sync_to_thread is not None:
            if is_sync_or_async_generator(dependency):
                warn_sync_to_thread_with_generator(dependency, stacklevel=3)
            elif not has_sync_callable:
                warn_sync_to_thread_with_async_callable(dependency, stacklevel=3)  # pyright: ignore
        elif has_sync_callable and not is_sync_or_async_generator(dependency):
            warn_implicit_sync_to_thread(dependency, stacklevel=3)

        if sync_to_thread and has_sync_callable:
            self.dependency = Ref["AnyCallable"](async_partial(dependency))  # pyright: ignore
            self.has_sync_callable = False
        else:
            self.dependency = Ref["AnyCallable"](dependency)  # pyright: ignore
            self.has_sync_callable = has_sync_callable

        self.sync_to_thread = bool(sync_to_thread)
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
