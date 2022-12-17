from inspect import isasyncgen
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    Generator,
    List,
    Optional,
    Type,
    Union,
)

from anyio import create_task_group

from starlite.types import Empty
from starlite.utils.compat import async_next
from starlite.utils.helpers import Ref
from starlite.utils.sync import AsyncCallable, is_async_callable

if TYPE_CHECKING:
    from inspect import Traceback

    from starlite.signature import SignatureModel
    from starlite.types import AnyCallable, AnyGenerator


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

    Simplify cleanup by wrapping `next`/`anext` calls and providing facilities to `throw` / `athrow` into all generators
    consecutively. An instance of this class can be used as a contextmanager, which will automatically throw any
    exceptions into its generators. All exceptions caught in this manner will be re-raised after they have been thrown
    in the generators.
    """

    __slots__ = ("_generators", "_closed")

    def __init__(self, generators: Optional[List["AnyGenerator"]] = None) -> None:
        """Initialize `DependencyCleanupGroup`.

        Args:
            generators: An optional list of generators to be called at cleanup
        """
        self._generators = generators or []
        self._closed = False

    def add(self, generator: Union[Generator[Any, None, None], AsyncGenerator[Any, None]]) -> None:
        """Add a new generator to the group.

        Args:
            generator: The generator to add

        Returns:
            None
        """
        if self._closed:
            raise RuntimeError("Cannot call cleanup on a closed DependencyCleanupGroup")
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

    async def cleanup(self) -> None:
        """Execute cleanup by calling `next` / `anext` on all generators.

        If there are multiple generators to be called, they will be executed in a `TaskGroup`.

        Returns:
            None
        """
        if self._closed:
            raise RuntimeError("Cannot call cleanup on a closed DependencyCleanupGroup")

        self._closed = True

        if not self._generators:
            return

        if len(self._generators) == 1:
            await self._wrap_next(self._generators[0])()
            return

        async with create_task_group() as task_group:
            for generator in self._generators:
                task_group.start_soon(self._wrap_next(generator))

    async def __aenter__(self) -> None:
        """Support the async contextmanager protocol to allow for easier catching and throwing of exceptions into the
        generators.
        """

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional["Traceback"],
    ) -> None:
        """If an exception was raised within the contextmanager block, throw it into all generators."""
        if exc_val:
            await self.throw(exc_val)

    async def throw(self, exc: BaseException) -> None:
        """Throw an exception in all generators sequentially.

        Args:
            exc: Exception to throw
        """
        for gen in self._generators:
            try:
                if isasyncgen(gen):
                    await gen.athrow(exc)
                else:
                    gen.throw(exc)  # type: ignore[union-attr]
            except (StopIteration, StopAsyncIteration):
                continue
