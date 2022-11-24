from inspect import isasyncgen
from typing import Any, AsyncGenerator, Callable, Coroutine, Generator, List, Optional, TYPE_CHECKING, Union

import anyio

from starlite.types import Empty
from starlite.utils.compat import async_next
from starlite.utils.helpers import Ref
from starlite.utils.sync import AsyncCallable, is_async_callable

if TYPE_CHECKING:
    from typing import Type

    from starlite.signature import SignatureModel
    from starlite.types import AnyCallable, AnyGenerator, Scope, Receive, Send, ASGIApp


class Provide:
    """A wrapper class for dependency injection."""

    __slots__ = (
        "dependency",
        "use_cache",
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


class DependencyCleanupGroup:
    """Wrapper for generator based dependencies.

    Simplify cleanup by wrapping `next`/`anext` calls in `BackgroundTasks` and providing facilities to `throw` /
    `athrow` into all generators consecutively.
    """

    def __init__(self, generators: Optional[List["AnyGenerator"]] = None) -> None:
        self._generators = generators or []

    def add(self, generator: Union[Generator[Any, None, None], AsyncGenerator[Any, None]]) -> None:
        self._generators.append(generator)

    @staticmethod
    def _wrap_next(generator: "AnyGenerator") -> Callable[[], Coroutine[None, None, None]]:
        if isasyncgen(generator):

            async def wrapped_async() -> None:
                await async_next(generator, None)  # type: ignore[arg-type]

            return wrapped_async

        def wrapped() -> None:
            next(generator, None)  # type: ignore[arg-type]

        return AsyncCallable(wrapped)

    def wrap_asgi(self, app: "ASGIApp") -> "ASGIApp":
        async def wrapped(scope: "Scope", receive: "Receive", send: "Send") -> None:
            if len(self._generators) == 1:
                await self._wrap_next(self._generators[0])()
            elif self._generators:
                async with anyio.create_task_group() as tg:
                    for gen in self._generators:
                        tg.start_soon(self._wrap_next(gen))
            await app(scope, receive, send)

        return wrapped

    async def throw(self, exc: Any) -> None:
        for gen in self._generators:
            try:
                if isasyncgen(gen):
                    await gen.athrow(exc)
                else:
                    gen.throw(exc)  # type: ignore[union-attr]
            except (StopIteration, StopAsyncIteration):
                continue
