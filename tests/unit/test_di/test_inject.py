# pyright: reportUnnecessaryTypeIgnoreComment=false
from __future__ import annotations

import contextvars
import functools
import threading
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

from litestar.di import (
    DIContext,
    DIRegistry,
    InjectionTarget,
    NamedDependency,
    Provider,
    TypeDependency,
    provide,
)
from litestar.di.exceptions import DIRegistrationError, MissingProviderError
from litestar.utils.signature import ParsedSignature


class Config:
    pass


@provide(scope="app", kind="type")
async def config() -> Config:
    return Config()


@pytest.fixture()
def session_factory() -> Mock:
    return MagicMock(return_value="session")


@pytest.fixture()
def session_provider(session_factory: MagicMock) -> Provider:
    @provide(scope="request")
    async def session() -> str:
        return session_factory()  # type: ignore[no-any-return]

    return session


@pytest.fixture()
async def request_context(session_provider: Provider) -> AsyncIterator[DIContext]:
    async with DIContext(DIRegistry("app", [config, session_provider])) as app_ctx, app_ctx.enter_nested() as request:
        yield request


async def test_inject_resolves_marked_parameters(request_context: DIContext) -> None:
    async def handler(session: NamedDependency[str], cfg: TypeDependency[Config]) -> str:
        return f"{session}/{type(cfg).__name__}"

    assert await request_context.inject(handler) == "session/Config"


@pytest.mark.parametrize(
    ("args", "kwargs"),
    [pytest.param(("req",), None, id="positional"), pytest.param((), {"request": "req"}, id="keyword")],
)
async def test_caller_fills_unmarked_parameter_without_default(
    args: tuple[Any, ...], kwargs: dict[str, Any] | None, request_context: DIContext
) -> None:
    async def handler(request: Any, session: NamedDependency[str]) -> str:
        return f"{request}:{session}"

    assert await request_context.inject(handler, args, kwargs) == "req:session"


async def test_inject_forwards_keyword_arguments(request_context: DIContext) -> None:
    async def handler(session: NamedDependency[str], page: int = 1) -> str:
        return f"{session}:{page}"

    assert await request_context.inject(handler, kwargs={"page": 7}) == "session:7"


async def test_caller_fills_unmarked_parameter_named_cls(request_context: DIContext) -> None:
    async def handler(cls: int) -> int:
        return cls

    assert await request_context.inject(handler, kwargs={"cls": 3}) == 3


async def test_caller_value_overrides_dependency_without_resolving(
    request_context: DIContext, session_factory: MagicMock
) -> None:

    async def handler(session: NamedDependency[str]) -> str:
        return session

    assert await request_context.inject(handler, kwargs={"session": "injected by hand"}) == "injected by hand"

    assert session_factory.call_count == 0


async def test_caller_value_kept_while_other_dependencies_resolve(
    request_context: DIContext, session_factory: MagicMock
) -> None:
    """With a second dependency in play the resolution pass runs; the caller's value is not replaced
    by the provider's in the fill that follows."""

    async def handler(session: NamedDependency[str], config: TypeDependency[Config]) -> str:
        return f"{session}:{type(config).__name__}"

    assert await request_context.inject(handler, kwargs={"session": "injected by hand"}) == "injected by hand:Config"

    assert session_factory.call_count == 0


async def test_explicitly_passed_dependency_is_not_resolved() -> None:
    # neither is 'engine', which only the passed 'session' depends on
    built: list[str] = []

    @provide(scope="app")
    async def engine() -> str:
        built.append("engine")
        return "engine"

    @provide(scope="app")
    async def session(engine: NamedDependency[str]) -> str:
        built.append("session")
        return "session"

    async def handler(session: NamedDependency[str]) -> str:
        return session

    async with DIContext(DIRegistry("app", [engine, session])) as ctx:
        assert await ctx.inject(handler, kwargs={"session": "passed in"}) == "passed in"

    assert built == []


async def test_target_variadics_receive_caller_arguments(request_context: DIContext) -> None:
    async def handler(*args: Any, session: NamedDependency[str], **kwargs: Any) -> str:
        return f"{args}:{session}:{sorted(kwargs)}"

    assert await request_context.inject(handler, (1, 2), {"extra": 3}) == "(1, 2):session:['extra']"


async def test_unresolvable_dependency_of_target_raises(request_context: DIContext) -> None:
    async def handler(nope: NamedDependency[str]) -> str:
        return nope

    with pytest.raises(MissingProviderError, match="'nope'"):
        await request_context.inject(handler)


async def test_missing_sync_to_thread(request_context: DIContext) -> None:

    def handler(session: NamedDependency[str]) -> str:
        return session

    with pytest.raises(DIRegistrationError, match="Missing 'sync_to_thread' on synchronous callable"):
        await request_context.inject(handler)


async def test_class_target_without_sync_to_thread(request_context: DIContext) -> None:
    # doesn't need it. __init__ is assumed to be non-blocking
    class Holder:
        def __init__(self, session: NamedDependency[str]) -> None:
            self.session = session
            self.thread = threading.current_thread().name

    holder = await request_context.inject(Holder)
    assert holder.session == "session"
    assert holder.thread == threading.current_thread().name


async def test_sync_generator_target_returns_the_generator(request_context: DIContext) -> None:
    def handler(session: NamedDependency[str]) -> Iterator[str]:
        yield session
        yield "more"

    generator = await request_context.inject(handler)

    assert list(generator) == ["session", "more"]


async def test_async_generator_target_returns_the_generator(request_context: DIContext) -> None:
    async def handler(session: NamedDependency[str]) -> AsyncIterator[str]:
        yield session
        yield "more"

    generator = await request_context.inject(handler)
    assert [item async for item in generator] == ["session", "more"]


async def test_class_target_gets_constructor_injection(request_context: DIContext) -> None:
    class Service:
        def __init__(self, session: NamedDependency[str], label: str = "svc") -> None:
            self.session = session
            self.label = label

    service = await request_context.inject(Service, kwargs={"label": "custom"})

    assert service.session == "session"
    assert service.label == "custom"


class MethodHandler:
    async def run(self, session: NamedDependency[str]) -> str:
        return session


class CallableHandler:
    async def __call__(self, session: NamedDependency[str]) -> str:
        return session


@pytest.mark.parametrize(
    "target",
    [pytest.param(MethodHandler().run, id="bound-method"), pytest.param(CallableHandler(), id="callable-instance")],
)
async def test_bound_method_or_callable_instance_target(target: Any, request_context: DIContext) -> None:
    assert await request_context.inject(target) == "session"


async def test_target_without_dependencies(request_context: DIContext) -> None:
    async def handler() -> str:
        return "plain"

    assert await request_context.inject(handler) == "plain"


async def test_inject_into_provider_raises(
    request_context: DIContext, session_factory: MagicMock, session_provider: Provider
) -> None:
    # they are regular callables, so we have an explicit check for them
    with pytest.raises(DIRegistrationError, match="is a Provider, not an injection target") as exc_info:
        await request_context.inject(session_provider)

    assert "produced once per scope and cached" in str(exc_info.value)
    assert session_factory.call_count == 0


def test_injection_target_repr() -> None:
    async def handler() -> None:
        return None

    assert repr(InjectionTarget(handler)) == f"InjectionTarget({handler!r})"


async def test_injection_target_cache(session_provider: Provider) -> None:

    async def handler(session: NamedDependency[str]) -> str:
        return session

    app_ctx = DIContext(DIRegistry("app", [config, session_provider]))
    async with app_ctx:
        async with app_ctx.enter_nested() as first:
            await first.inject(handler)
        kept = handler.__litestar_injection_target__  # type: ignore[attr-defined]
        assert isinstance(kept, InjectionTarget) and kept._fn is handler

        async with app_ctx.enter_nested() as second:
            await second.inject(handler)
        assert handler.__litestar_injection_target__ is kept  # type: ignore[attr-defined]

        explicit = InjectionTarget(handler)
        async with app_ctx.enter_nested() as third:
            assert await third.inject(explicit) == "session"
        assert handler.__litestar_injection_target__ is kept  # type: ignore[attr-defined]


async def test_non_cacheable_injection_target(request_context: DIContext) -> None:
    class Service:
        async def handle(self, session: NamedDependency[str]) -> str:
            return session

    @dataclass(frozen=True)
    class Frozen:
        name: str

        async def __call__(self, session: NamedDependency[str]) -> str:
            return f"{self.name}:{session}"

    service, frozen = Service(), Frozen("frozen")
    assert await request_context.inject(service.handle) == "session"
    assert await request_context.inject(service.handle) == "session"
    assert await request_context.inject(frozen) == "frozen:session"
    assert not hasattr(frozen, "__litestar_injection_target__")
    assert not hasattr(service.handle, "__litestar_injection_target__")


async def test_equal_but_distinct_callables_are_distinct_injection_targets(request_context: DIContext) -> None:
    # test is mainly to prevent regressions in the caching mechanism, e.g. something
    # that cached based on equality

    @dataclass(frozen=True)
    class Handler:
        name: str
        behaviour: str = field(default="", compare=False)

        async def __call__(self, session: NamedDependency[str]) -> str:
            return f"{self.behaviour}:{session}"

    class Both:
        def __init__(self, session: NamedDependency[str]) -> None:
            self.session = session

        async def __call__(self, session: NamedDependency[str]) -> str:
            return f"instance:{session}"

    assert Handler("h", "first") == Handler("h", "second")
    assert await request_context.inject(Handler("h", "first")) == "first:session"
    assert await request_context.inject(Handler("h", "second")) == "second:session"

    instance = await request_context.inject(Both)  # the class: its __init__ is filled
    assert instance.session == "session"
    assert Both.__litestar_injection_target__._fn is Both  # type: ignore[attr-defined]
    assert await request_context.inject(instance) == "instance:session"  # the instance: its __call__
    assert instance.__litestar_injection_target__._fn is instance  # type: ignore[attr-defined]


async def test_positional_argument_overrides_dependency_it_lands_on() -> None:
    """The same as passing it by keyword."""
    calls = 0

    @provide(scope="app")
    async def db() -> str:
        nonlocal calls
        calls += 1
        return "db"

    async def handler(db: NamedDependency[str], page: int = 1) -> str:
        return f"{db}/{page}"

    async with DIContext(DIRegistry("app", [db])) as ctx:
        assert await ctx.inject(handler, ("supplied",)) == "supplied/1"
        assert await ctx.inject(handler, ("supplied", 2)) == "supplied/2"
        assert await ctx.inject(handler, kwargs={"db": "supplied"}) == "supplied/1"

    assert calls == 0  # the factory it replaced never ran, either way


async def test_positional_arguments_before_dependency_do_not_collide() -> None:
    @provide(scope="app")
    async def db() -> str:
        return "db"

    async def handler(page: int, db: NamedDependency[str]) -> str:
        return f"{db}/{page}"

    async with DIContext(DIRegistry("app", [db])) as ctx:
        assert await ctx.inject(handler, (2,)) == "db/2"


async def test_positional_argument_lands_after_partial_binding_with_given_signature() -> None:
    """The signature is the wrapped callable's, the way litestar parses a handler."""

    async def handler(db: NamedDependency[str], page: NamedDependency[int]) -> str:
        return f"{db}/{page}"

    bound = functools.partial(handler, "bound")
    target = InjectionTarget(bound, signature=ParsedSignature.from_fn(handler, {}))

    async with DIContext(DIRegistry("app", [])) as ctx:
        assert await ctx.inject(target, (2,)) == "bound/2"


async def test_dependency_behind_var_positional_does_not_collide() -> None:
    """Anything marked after ``*args`` is keyword-only, so no positional argument reaches it."""

    @provide(scope="app")
    async def db() -> str:
        return "db"

    async def handler(*pages: int, db: NamedDependency[str]) -> str:
        return f"{db}/{sum(pages)}"

    async with DIContext(DIRegistry("app", [db])) as ctx:
        assert await ctx.inject(handler, (1, 2, 3)) == "db/6"


async def test_caller_value_overrides_a_bound_optional_dependency() -> None:
    @provide(scope="app", key="name")
    async def name() -> str:
        return "di"

    async def handler(name: NamedDependency[str] = "world") -> str:
        return f"hello {name}"

    async with DIContext(DIRegistry("app", [name])) as ctx:
        assert await ctx.inject(handler, kwargs={"name": "caller"}) == "hello caller"


async def test_sync_to_thread_kwarg_passed_to_target(request_context: DIContext) -> None:

    async def handler(session: NamedDependency[str], sync_to_thread: bool = False) -> tuple[str, bool]:
        return session, sync_to_thread

    assert await request_context.inject(handler, kwargs={"sync_to_thread": True}) == ("session", True)


async def test_inject_does_not_mutate_caller_kwargs(request_context: DIContext) -> None:
    async def handler(session: NamedDependency[str], page: int = 1) -> str:
        return f"{session}/{page}"

    given = {"page": 2}
    assert await request_context.inject(handler, kwargs=given) == "session/2"
    assert given == {"page": 2}


async def test_sync_target_runs_where_sync_to_thread_says(request_context: DIContext) -> None:
    """``sync_to_thread=True`` keeps a blocking target off the loop; ``False`` runs a
    non-blocking one inline, in the caller's context."""
    seen: contextvars.ContextVar[str] = contextvars.ContextVar("seen", default="unset")

    def handler(session: NamedDependency[str]) -> str:
        seen.set(session)
        return threading.current_thread().name

    assert await request_context.inject(handler, sync_to_thread=True) != threading.current_thread().name
    assert seen.get() == "unset"  # set in a copy of the context, in the worker thread

    assert await request_context.inject(handler, sync_to_thread=False) == threading.current_thread().name
    assert seen.get() == "session"
