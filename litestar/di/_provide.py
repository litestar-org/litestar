from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.utils.deprecation import warn_deprecation

if TYPE_CHECKING:
    from litestar.types import AnyCallable

__all__ = ("Provide",)


class Provide:
    """A dependency declaration, converted at handler registration to a
    :class:`~litestar.di.Provider` of ``dependency`` under the key it is declared with: scope
    ``"app"`` with ``use_cache=True``, ``"handler"`` otherwise, and ``sync_to_thread`` as given.
    """

    __slots__ = ("dependency", "sync_to_thread", "use_cache")

    def __init__(
        self,
        dependency: AnyCallable | type[Any],
        use_cache: bool = False,
        sync_to_thread: bool | None = None,
    ) -> None:
        """Store the arguments, warning that ``Provide`` is deprecated.

        Args:
            dependency: The factory callable
            use_cache: Whether the provider has scope ``"app"`` instead of ``"handler"``
            sync_to_thread: Whether a sync callable runs in a worker thread
        """
        warn_deprecation(
            version="3.0",
            deprecated_name="Provide",
            kind="class",
            removal_in="4.0",
            alternative="litestar.di.Provider",
            info="Provide(fn, use_cache, sync_to_thread) is Provider(fn, key=<the key it is declared under>, "
            "scope='app' if use_cache else 'handler', sync_to_thread=sync_to_thread)",
            stacklevel=3,
        )
        self.dependency = dependency
        self.use_cache = use_cache
        self.sync_to_thread = sync_to_thread
