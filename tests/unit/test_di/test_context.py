# pyright: reportUnnecessaryTypeIgnoreComment=false, enableExperimentalFeatures=true
from __future__ import annotations

import abc
import asyncio
import functools
from collections.abc import AsyncGenerator
from typing import Annotated, Any, Literal, NewType, Protocol, assert_type

import pytest
from pytest_mock import MockerFixture

from litestar.di import (
    Dependency,
    DependencyKey,
    DIContext,
    DIRegistry,
    InjectionTarget,
    NamedDependency,
    Provider,
    TypeDependency,
    provide,
)
from litestar.di.exceptions import (
    CaptiveDependencyError,
    CircularDependencyError,
    DIContextClosedError,
    DIRegistrationError,
    DIResolutionError,
    DIScopeError,
    MissingProviderError,
    MissingSeedError,
    ScopeMismatchError,
)
from tests.unit.test_di.helpers import CallWithDependencies, Resolve


class Config:
    pass


@provide(scope="app", kind="type")
async def config() -> Config:
    return Config()


@provide(scope="app")
async def app_value() -> object:
    return object()


@provide(scope="request")
async def request_value() -> object:
    return object()


@provide(scope="handler")
async def handler_value() -> object:
    return object()


@pytest.fixture()
def full_registry() -> DIRegistry:
    return DIRegistry("app", [config, app_value, request_value, handler_value])


def slot_key(registry: DIRegistry, provider: Provider) -> tuple[Provider, frozenset[Provider]]:
    return provider, registry.predecessors_of(provider)


async def test_root_context_defaults_to_outermost_scope(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as ctx:
        assert ctx.scope == "app"


async def test_root_context_with_non_root_scope_raises(full_registry: DIRegistry) -> None:
    with pytest.raises(DIScopeError, match="has to use the outermost scope 'app'"):
        DIContext(full_registry, scope="request")


async def test_unknown_scope_raises(full_registry: DIRegistry) -> None:
    with pytest.raises(DIScopeError, match="has no scope 'nope'"):
        DIContext(full_registry, scope="nope")


async def test_nested_context_defaults_to_next_scope(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as app_ctx, app_ctx.enter_nested() as nested:
        assert nested.scope == "request"
        async with nested.enter_nested() as inner:
            assert inner.scope == "handler"


@pytest.mark.parametrize("scope", [pytest.param("handler", id="skipping"), pytest.param("app", id="repeating")])
async def test_entering_scope_out_of_order_raises(full_registry: DIRegistry, scope: str) -> None:
    async with DIContext(full_registry) as app_ctx:
        with pytest.raises(
            DIScopeError, match=f"Cannot enter scope '{scope}' out of order. '{scope}' does not directly follow 'app'"
        ):
            DIContext(app_ctx.registry, scope=scope, parent=app_ctx)


async def test_nesting_below_innermost_scope_raises(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as app_ctx, app_ctx.enter_nested() as req, req.enter_nested() as handler:
        with pytest.raises(DIScopeError, match="is the innermost scope"):
            async with handler.enter_nested():
                pass


async def test_nesting_inside_innermost_scope_with_explicit_scope_raises(full_registry: DIRegistry) -> None:
    async with (
        DIContext(full_registry) as app_ctx,
        app_ctx.enter_nested() as req_ctx,
        req_ctx.enter_nested() as handler,
    ):
        with pytest.raises(
            DIScopeError, match="Cannot enter scope 'app' out of order. 'app' does not directly follow 'handler'"
        ):
            DIContext(handler.registry, scope="app", parent=handler)


async def test_nesting_inside_closed_context_raises(full_registry: DIRegistry) -> None:
    registry = full_registry
    ctx = DIContext(registry)
    await ctx.__aexit__(None, None, None)

    with pytest.raises(DIContextClosedError, match="Cannot open DIContext for scope 'request' with closed parent"):
        DIContext(registry, scope="request", parent=ctx)


async def test_value_stored_in_context_owning_its_scope(full_registry: DIRegistry) -> None:
    registry = full_registry
    async with DIContext(registry) as app_ctx, app_ctx.enter_nested() as req_ctx:
        # resolved from the request context, but the provider is app scoped
        value = await req_ctx.solve("app_value")

        assert app_ctx.get("app_value") is value
        assert not req_ctx.has_solved("app_value")
        assert app_ctx.has_solved("app_value")


async def test_slots_keyed_by_value_node_and_created_lazily(full_registry: DIRegistry) -> None:
    registry = full_registry
    async with DIContext(registry) as app_ctx:
        assert app_ctx._slots == {}  # nothing resolved, nothing allocated

        await app_ctx.solve("app_value")
        assert app_ctx._slots.keys() == {slot_key(registry, app_value)}
        assert app_ctx._slots[slot_key(registry, app_value)].provider is app_value
        assert app_value not in app_ctx._slots  # type: ignore[comparison-overlap]  # the provider alone is not a slot key

        await app_ctx.solve(Config)
        assert app_ctx._slots.keys() == {slot_key(registry, app_value), slot_key(registry, config)}

    seeded = DIRegistry("app", [Provider.seed("seeded_value", scope="app")])
    async with DIContext(seeded, seeds={"seeded_value": "supplied"}) as app_ctx:
        assert await app_ctx.solve("seeded_value") == "supplied"
        assert app_ctx._slots == {}  # a seed has no slot


async def test_app_scoped_values_shared_between_sibling_requests(full_registry: DIRegistry, resolve: Resolve) -> None:
    async with DIContext(full_registry) as app_ctx:
        async with app_ctx.enter_nested() as first:
            shared = await resolve(first, "app_value")
            scoped_first = await resolve(first, "request_value")
        async with app_ctx.enter_nested() as second:
            assert await resolve(second, "app_value") is shared
            assert await resolve(second, "request_value") is not scoped_first


async def test_request_scoped_values_shared_within_request(full_registry: DIRegistry, resolve: Resolve) -> None:
    async with DIContext(full_registry) as app_ctx, app_ctx.enter_nested() as req:
        first = await resolve(req, "request_value")
        async with req.enter_nested() as handler:
            assert await resolve(handler, "request_value") is first


async def test_solve_many(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as app_ctx, app_ctx.enter_nested() as req:
        values = await req.solve_many("app_value", "request_value", Config)

        assert values == (req.get("app_value"), req.get("request_value"), req.get(Config))
        assert isinstance(values[2], Config)


async def test_solve_many_values_typed_by_type_keys() -> None:
    class Engine:
        pass

    class Session:
        pass

    registry = DIRegistry(
        "app",
        [config, app_value, Provider(Engine, kind="type", scope="app"), Provider(Session, kind="type", scope="app")],
    )
    async with DIContext(registry) as ctx:
        assert_type(await ctx.solve_many(Config), tuple[Config])
        assert_type(await ctx.solve_many(Config, Engine), tuple[Config, Engine])
        values = assert_type(await ctx.solve_many(Config, Engine, Session), tuple[Config, Engine, Session])
        assert [type(value) for value in values] == [Config, Engine, Session]
        assert_type(await ctx.solve_many(Config, "app_value"), tuple[Any, ...])


async def test_solve_many_without_keys(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as ctx:
        assert await ctx.solve_many() == ()


async def test_solve_many_resolves_repeated_key_once() -> None:
    calls = 0

    @provide(scope="app")
    async def counted() -> int:
        nonlocal calls
        calls += 1
        return 1

    async with DIContext(DIRegistry("app", [counted])) as ctx:
        assert await ctx.solve_many("counted", "counted") == (1, 1)

    assert calls == 1


async def test_solve_arguments_returns_dependencies_by_parameter_name() -> None:
    calls: list[Any] = []

    @provide(scope="app")
    async def session() -> str:
        return "the session"

    async def handler(db: Annotated[str, Dependency("session")], limit: int = 10) -> None:
        calls.append((db, limit))

    async with DIContext(DIRegistry("app", [session])) as ctx:
        assert await ctx.solve_arguments(handler) == {"db": "the session"}
    assert calls == []


async def test_solve_arguments_accepts_an_injection_target() -> None:
    @provide(scope="app")
    async def session() -> str:
        return "the session"

    async def handler(session: NamedDependency[str]) -> None:
        pass

    async with DIContext(DIRegistry("app", [session])) as ctx:
        assert await ctx.solve_arguments(InjectionTarget(handler)) == {"session": "the session"}


async def test_supplied_parameters_are_neither_resolved_nor_looked_up() -> None:
    @provide(scope="app")
    async def session() -> str:
        return "the session"

    async def handler(session: NamedDependency[str], user: NamedDependency[str]) -> None:
        pass

    async with DIContext(DIRegistry("app", [session])) as ctx:
        assert await ctx.solve_arguments(handler, supplied={"session", "user"}) == {}
        assert not ctx.has_solved("session")


async def test_solve_arguments_resolves_parameters_not_supplied() -> None:
    @provide(scope="app")
    async def session() -> str:
        return "the session"

    async def handler(session: NamedDependency[str], user: NamedDependency[str]) -> None:
        pass

    async with DIContext(DIRegistry("app", [session])) as ctx:
        assert await ctx.solve_arguments(handler, supplied={"user"}) == {"session": "the session"}


async def test_supplied_name_without_parameter_raises() -> None:
    @provide(scope="app")
    async def session() -> str:
        return "the session"

    async def handler(session: NamedDependency[str], limit: int = 10) -> None:
        pass

    async with DIContext(DIRegistry("app", [session])) as ctx:
        with pytest.raises(
            DIResolutionError,
            match=r"Cannot solve the arguments of .*handler .*: 'supplied' names parameters it does not "
            r"declare: 'sesion'$",  # codespell:ignore
        ):
            await ctx.solve_arguments(handler, supplied={"limit", "sesion"})  # codespell:ignore
        assert not ctx.has_solved("session")


async def test_target_with_var_keyword_accepts_any_supplied_name() -> None:
    @provide(scope="app")
    async def session() -> str:
        return "the session"

    async def handler(session: NamedDependency[str], **extra: Any) -> None:
        pass

    async with DIContext(DIRegistry("app", [session])) as ctx:
        assert await ctx.solve_arguments(handler, supplied={"anything"}) == {"session": "the session"}


async def test_solve_arguments_from_inside_a_provider_raises() -> None:
    holder: dict[str, DIContext] = {}

    async def handler(session: NamedDependency[str]) -> None:
        pass

    @provide(scope="request")
    async def inner() -> str:
        await holder["ctx"].solve_arguments(handler)
        return "inner"

    async with DIContext(DIRegistry("app", [inner])) as app, app.enter_nested() as request:
        holder["ctx"] = request
        with pytest.raises(
            DIResolutionError,
            match=r"'DIContext\.solve_arguments\(\)' of.*used from inside the provider producing 'inner'",
        ):
            await request.solve("inner")


async def test_solve_unknown_key_raises(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as ctx:
        with pytest.raises(MissingProviderError, match="has no provider for dependency 'nope'") as exc_info:
            await ctx.solve("nope")

    assert exc_info.value.key == "nope"


async def test_solve_type_dependency() -> None:
    @provide(scope="request", kind="type")
    async def repo(cfg: TypeDependency[Config]) -> str:
        return f"repo for {type(cfg).__name__}"

    registry = DIRegistry("app", [config, repo])
    async with DIContext(registry) as app_ctx, app_ctx.enter_nested() as req:
        assert await req.solve(str) == "repo for Config"


UserId = NewType("UserId", int)
Mode = Literal["read", "write"]


async def test_value_typed_by_type_form_key() -> None:
    @provide(scope="app", kind="type")
    async def user_id() -> UserId:
        return UserId(7)

    @provide(scope="app", kind="type")
    async def mode() -> Mode:
        return "read"

    @provide(scope="app", kind="type")
    async def numbers() -> list[int]:
        return [1, 2]

    async with DIContext(DIRegistry("app", [user_id, mode, numbers])) as ctx:
        assert assert_type(await ctx.solve(UserId), UserId) == 7
        assert assert_type(await ctx.solve(Mode), Literal["read", "write"]) == "read"
        assert assert_type(await ctx.solve(list[int]), list[int]) == [1, 2]

        assert assert_type(ctx.get(UserId), UserId) == 7
        assert assert_type(ctx.get(Mode), Literal["read", "write"]) == "read"
        assert assert_type(ctx.get(list[int]), list[int]) == [1, 2]

        values = assert_type(
            await ctx.solve_many(UserId, Mode, list[int]), tuple[UserId, Literal["read", "write"], list[int]]
        )
        assert values == (7, "read", [1, 2])


async def test_value_typed_by_abstract_class_key() -> None:
    class Repository(Protocol):
        def load(self) -> str: ...

    class Storage(abc.ABC):
        @abc.abstractmethod
        def read(self) -> str: ...

    class SQLRepository:
        def load(self) -> str:
            return "row"

    class DiskStorage(Storage):
        def read(self) -> str:
            return "bytes"

    registry = DIRegistry(
        "app",
        [Provider(SQLRepository, scope="app", key=Repository), Provider(DiskStorage, scope="app", key=Storage)],
    )
    async with DIContext(registry) as ctx:
        repository = assert_type(await ctx.solve(Repository), Repository)
        storage = assert_type(await ctx.solve(Storage), Storage)
        assert (repository.load(), storage.read()) == ("row", "bytes")

        assert assert_type(ctx.get(Repository), Repository) is repository
        assert assert_type(ctx.get(Storage), Storage) is storage

        values = assert_type(await ctx.solve_many(Repository, Storage), tuple[Repository, Storage])
        assert values == (repository, storage)


async def test_name_key_spelling_a_type_typed_as_any() -> None:
    @provide(scope="app", key="Config")
    async def named() -> str:
        return "by name"

    # a string spelling a type is a type form: the overloads taking a 'str' have to match first
    async with DIContext(DIRegistry("app", [named, config])) as ctx:
        assert assert_type(await ctx.solve("Config"), Any) == "by name"
        assert assert_type(ctx.get("Config"), Any) == "by name"
        assert assert_type(await ctx.solve_many("Config"), tuple[Any, ...]) == ("by name",)
        assert_type(await ctx.solve_many(Config, "Config"), tuple[Any, ...])
        assert_type(await ctx.solve_many(Config, Config, "Config"), tuple[Any, ...])


async def test_new_type_type_dependency() -> None:
    # a NewType should be treated as a distinct type

    @provide(scope="app", kind="type")
    async def user_id() -> UserId:
        return UserId(7)

    @provide(scope="app", kind="type")
    async def count() -> int:
        return 3

    async def handler(user: TypeDependency[UserId], total: TypeDependency[int]) -> tuple[int, int]:
        return user, total

    assert user_id.key is UserId
    assert count.key is int
    async with DIContext(DIRegistry("app", [user_id, count])) as ctx:
        assert await ctx.inject(handler) == (7, 3)
        assert await ctx.solve(UserId) == 7
        assert await ctx.solve(int) == 3

    async with DIContext(DIRegistry("app", [user_id])) as ctx:
        with pytest.raises(MissingProviderError, match="dependency int"):
            await ctx.solve(int)


@provide(scope="app")
async def leaky(request_value: NamedDependency[object]) -> object:
    return request_value


async def test_app_provider_depending_on_request_value_raises() -> None:
    registry = DIRegistry("app", [request_value, leaky])
    with pytest.raises(CaptiveDependencyError) as exc_info:
        registry.freeze()

    message = str(exc_info.value)
    assert message.startswith(
        "Provider 'leaky' with scope 'app' depends on 'request_value' with scope 'request'. "
        "Since scope 'request' descends from scope 'app', providers with scope 'app' "
        "cannot depend on values from scope 'request'"
    )
    assert "scope order: 'app' -> 'request' -> 'handler'" in message
    assert "registry: 'app'" in message
    assert exc_info.value.key == "leaky"
    assert exc_info.value.dependency_key == "request_value"

    # a failed freeze does not lock the registry, and a context cannot be built over the bug.
    assert registry.is_frozen is False
    with pytest.raises(CaptiveDependencyError):
        DIContext(registry)


@provide(scope="request")
async def per_request(handler_value: NamedDependency[object]) -> object:
    return handler_value


@provide(scope="app")
async def optional_leaky(request_value: NamedDependency[object] = None) -> object:
    return request_value


@provide(scope="app")
async def seed_leaky(request_obj: NamedDependency[object]) -> object:
    return request_obj


@pytest.mark.parametrize(
    "providers",
    [
        pytest.param([per_request, handler_value], id="request-on-handler"),
        pytest.param([optional_leaky, request_value], id="optional-dependency"),
        pytest.param([seed_leaky, Provider.seed("request_obj", scope="request")], id="seed"),
    ],
)
async def test_captive_dependency_raises(providers: list[Provider]) -> None:
    with pytest.raises(CaptiveDependencyError):
        DIRegistry("app", providers).freeze()


async def test_dependency_on_preceding_scope() -> None:
    # a request provider can have an app dependency
    @provide(scope="request")
    async def uses_app(app_value: NamedDependency[object]) -> object:
        return app_value

    registry = DIRegistry("app", [app_value, uses_app])
    async with DIContext(registry) as app_ctx, app_ctx.enter_nested() as req:
        assert await req.solve("uses_app") is await app_ctx.solve("app_value")


async def test_scope_not_entered_raises(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as app_ctx, app_ctx.enter_nested() as req:
        with pytest.raises(
            ScopeMismatchError,
            match=(
                "Cannot resolve dependency 'handler_value' through scope 'request'. "
                "Its scope 'handler' does not match that of the current context, or "
                "any of its parents"
            ),
        ):
            await req.solve("handler_value")


async def test_get(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as ctx:
        value = await ctx.solve("app_value")
        assert ctx.get("app_value") is value


async def test_get_from_parent(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as app_ctx, app_ctx.enter_nested() as req:
        value = await app_ctx.solve("app_value")
        assert req.get("app_value") is value


async def test_get_unsolved_raises(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as ctx:
        with pytest.raises(DIResolutionError, match="has not been resolved"):
            ctx.get("app_value")


async def test_get_unknown_key_raises(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as ctx:
        with pytest.raises(DIResolutionError, match="'nope'"):
            ctx.get("nope")


async def test_get_has_no_side_effects() -> None:
    # it shouldn't. just to be sure :)
    @provide(scope="app")
    async def cfg() -> str:
        return "REAL"

    @provide(scope="app", key="cfg")
    async def fake_cfg() -> str:
        return "FAKE"

    base = DIRegistry("base", [cfg])
    overrides = DIRegistry("overrides", [fake_cfg])

    async with DIContext(base) as app_ctx:
        assert await app_ctx.solve("cfg") == "REAL"

        async with DIContext(overrides, scope="request", parent=app_ctx) as req:
            with pytest.raises(DIResolutionError, match="has not been resolved"):
                req.get("cfg")  # 'REAL' is there, under base's provider, and stays out of reach
            assert app_ctx._slots.keys() == {slot_key(base, cfg)}  # the failed read created nothing

            assert await req.solve("cfg") == "FAKE"
            assert req.get("cfg") == "FAKE"
            assert app_ctx.get("cfg") == "REAL"


async def test_set_explicit_name_key_on_parameter(call_with_dependencies: CallWithDependencies) -> None:

    @provide(scope="app", key="db.session")
    async def make_session() -> str:
        return "the session"

    async def repo(session: Annotated[str, Dependency("db.session")]) -> str:
        return f"repo({session})"

    assert await call_with_dependencies(repo, [make_session]) == "repo(the session)"


async def test_set_explicit_type_key_on_parameter(call_with_dependencies: CallWithDependencies) -> None:
    the_config = Config()

    @provide(scope="app", kind="type")
    async def config() -> Config:
        return the_config

    async def reader(settings: Annotated[Config, Dependency(Config)]) -> Config:
        return settings

    assert await call_with_dependencies(reader, [config]) is the_config


async def test_optional_dependency_without_provider(call_with_dependencies: CallWithDependencies) -> None:
    # should still solve
    async def greeting(name: NamedDependency[str] = "world") -> str:
        return f"hello {name}"

    assert await call_with_dependencies(greeting, []) == "hello world"


async def test_optional_dependency_with_provider(call_with_dependencies: CallWithDependencies) -> None:
    # provider should take precedence
    async def greeting(name: NamedDependency[str] = "world") -> str:
        return f"hello {name}"

    @provide(scope="app", key="name")
    async def provide_name() -> str:
        return "di"

    assert await call_with_dependencies(greeting, [provide_name]) == "hello di"


async def test_explicit_marker_with_default_is_optional(call_with_dependencies: CallWithDependencies) -> None:
    async def message(salutation: Annotated[str, Dependency("greeting")] = "hi") -> str:
        return salutation

    assert await call_with_dependencies(message, []) == "hi"


async def test_optional_union_dependency_with_provider(
    call_with_dependencies: CallWithDependencies,
) -> None:
    async def greeting(name: NamedDependency[str] | None = None) -> str:
        return f"hello {name}"

    @provide(scope="app", key="name")
    async def provide_name() -> str:
        return "di"

    assert await call_with_dependencies(greeting, [provide_name]) == "hello di"


async def test_optional_type_dependency_resolves_from_explicitly_keyed_provider(
    call_with_dependencies: CallWithDependencies,
) -> None:
    """``TypeDependency[T | None]`` resolves the key ``T``. A factory annotated ``-> T | None``
    cannot infer a key (it would be ``T | None``, never found); with the key given, the two meet."""

    @provide(scope="app", kind="type", key=Config)
    async def maybe_config() -> Config | None:
        return Config()

    async def reader(config: TypeDependency[Config | None] = None) -> Config | None:
        return config

    assert isinstance(await call_with_dependencies(reader, [maybe_config]), Config)


async def test_partial_keyword_binding_is_not_resolved(call_with_dependencies: CallWithDependencies) -> None:
    @provide(scope="app", key="name")
    async def provide_name() -> str:
        return "di"

    async def greeting(name: NamedDependency[str]) -> str:
        return f"hello {name}"

    bound = functools.partial(greeting, name="bound")

    assert await call_with_dependencies(bound, [provide_name]) == "hello bound"


@provide(scope="app")
async def needs_cfg(cfg: NamedDependency[str]) -> str:
    return cfg


@provide(scope="app")
async def wants_cfg(cfg: NamedDependency[str] = "default") -> str:
    return cfg


@pytest.mark.parametrize("dependent", [pytest.param(needs_cfg, id="required"), pytest.param(wants_cfg, id="optional")])
async def test_unseeded_seed_raises_at_construction(dependent: Provider) -> None:
    with pytest.raises(MissingSeedError):
        DIContext(DIRegistry("app", [dependent, Provider.seed("cfg", scope="app")]))


async def test_seeds_supply_declared_key() -> None:
    seed = Provider.seed("value", scope="app")
    async with DIContext(DIRegistry("app", [seed]), seeds={"value": "supplied"}) as ctx:
        assert await ctx.solve("value") == "supplied"
        assert ctx.get("value") == "supplied"


async def test_seed_key_reads_seeded_value(resolve: Resolve) -> None:
    registry = DIRegistry("app", [Provider.seed("request_obj", scope="request")])
    marker = object()

    async with DIContext(registry) as app_ctx, app_ctx.enter_nested(seeds={"request_obj": marker}) as req:
        assert await resolve(req, "request_obj") is marker
        assert req.get("request_obj") is marker


async def test_seed_has_been_solved_in_context_seeded_with_it() -> None:
    registry = DIRegistry("app", [Provider.seed("cfg", scope="app")])

    async with DIContext(registry, seeds={"cfg": "value"}) as app_ctx, app_ctx.enter_nested() as req:
        assert app_ctx.has_solved("cfg")
        assert not req.has_solved("cfg")


async def test_contexts_seeds_isolated_with_shared_registry() -> None:
    # regression test: caught a bug where seeding with a shared registry would make
    # seeds leak into subsequent contexts
    registry = DIRegistry("app", [Provider.seed("request_obj", scope="request")])

    async with DIContext(registry) as app_ctx:
        async with app_ctx.enter_nested(seeds={"request_obj": "first"}) as req:
            assert await req.solve("request_obj") == "first"
        async with app_ctx.enter_nested(seeds={"request_obj": "second"}) as req:
            assert await req.solve("request_obj") == "second"


async def test_provider_with_seed_dependency() -> None:

    @provide(scope="request")
    async def current_user(request_obj: NamedDependency[dict[str, str]]) -> str:
        return request_obj["user"]

    registry = DIRegistry("app", [current_user, Provider.seed("request_obj", scope="request")])

    async with DIContext(registry) as app_ctx, app_ctx.enter_nested(seeds={"request_obj": {"user": "alice"}}) as req:
        assert await req.solve("current_user") == "alice"


async def test_dependent_of_seed_reads_seeded_value() -> None:
    @provide(scope="app", key="reader")
    async def reader(cfg: NamedDependency[str]) -> str:
        return f"reader({cfg})"

    registry = DIRegistry("app", [reader, Provider.seed("cfg", scope="app")])
    async with DIContext(registry, seeds={"cfg": "from-outside"}) as ctx:
        assert await ctx.solve("reader") == "reader(from-outside)"


async def test_missing_seed_raises() -> None:
    registry = DIRegistry("app", [Provider.seed("request_obj", scope="request")])

    async with DIContext(registry) as app_ctx:
        with pytest.raises(
            MissingSeedError,
            match=(
                "Registry 'app' declares 'request_obj' as a seed at scope 'request', but context "
                r"<DIContext \[not entered\] scope='request' registry='app' at .*> "
                r"was not provided the value. \(seeded=\[\]\)"
            ),
        ):
            app_ctx.enter_nested()


async def test_seed_with_factory_raises() -> None:
    calls = 0

    @provide(scope="app")
    async def value() -> str:
        nonlocal calls
        calls += 1
        return "factory"

    registry = DIRegistry("app", [value])
    with pytest.raises(DIRegistrationError, match="it is produced by provider"):
        DIContext(registry, seeds={"value": "supplied"})
    async with DIContext(registry) as ctx:
        assert await ctx.solve("value") == "factory"

    assert calls == 1


@pytest.mark.parametrize("seeds", [{"reqest_obj": 1}, {"request_obj": 1, "reqest_obj": 2}])  # codespell:ignore
async def test_seed_for_undeclared_key_raises(seeds: dict[DependencyKey, int]) -> None:
    registry = DIRegistry("app", [Provider.seed("request_obj", scope="app")])
    with pytest.raises(DIRegistrationError, match="seeded with 'reqest_obj'") as exc_info:  # codespell:ignore
        DIContext(registry, seeds=seeds)
    message = str(exc_info.value)
    assert "did you mean: 'request_obj'?" in message
    assert "declared here: 'request_obj'" in message


async def test_seed_declared_in_higher_scope_raises() -> None:
    registry = DIRegistry("app", [Provider.seed("app_seed", scope="app")])
    async with DIContext(registry, seeds={"app_seed": "real"}) as app_ctx:
        with pytest.raises(DIRegistrationError, match="it is declared as a seed at scope 'app'") as exc_info:
            app_ctx.enter_nested(seeds={"app_seed": "shadow"})

    assert "Pass it to the context with scope 'app' instead" in str(exc_info.value)


async def test_seed_declared_in_lower_scope_raises() -> None:
    registry = DIRegistry("app", [Provider.seed("request_seed", scope="request")])
    with pytest.raises(DIRegistrationError, match="it is declared as a seed at scope 'request'"):
        DIContext(registry, seeds={"request_seed": "supplied at app scope"})


@provide(scope="app")
async def cached() -> int:
    return 1


async def test_nested_context_resolve_through_multiple_registries() -> None:
    app_registry = DIRegistry("app", [])
    route_registry = DIRegistry("route", [cached])
    other_route_registry = DIRegistry("other-route", [cached])
    async with DIContext(app_registry) as app_ctx:
        for _ in range(2):
            async with DIContext(route_registry, parent=app_ctx) as req:
                assert await req.solve("cached") == 1
            async with DIContext(other_route_registry, parent=app_ctx) as req:
                assert await req.solve("cached") == 1  # another registry, the same node, the same slot
        assert app_ctx._slots.keys() == {slot_key(route_registry, cached)}

        async with app_ctx.enter_nested(route_registry, seeds=None) as req:
            assert req.registry is route_registry
            assert req.parent is app_ctx
            assert req.scope == "request"
        async with app_ctx.enter_nested() as req:  # default: this context's registry
            assert req.registry is app_ctx.registry


@pytest.mark.parametrize(
    "providers",
    [
        pytest.param([], id="empty"),
        pytest.param([cached], id="app-scoped"),
        pytest.param([request_value], id="request-scoped"),
    ],
)
async def test_registry_created_after_outer_context_entered_raises(providers: list[Provider]) -> None:
    async with DIContext(DIRegistry("app", [cached])) as app_ctx:
        with pytest.raises(DIRegistrationError, match="was created after .* was entered"):
            app_ctx.enter_nested(DIRegistry("per-request", providers))
        with pytest.raises(DIRegistrationError, match="was created after .* was entered"):
            DIContext(DIRegistry("per-request", providers), parent=app_ctx)


async def test_registry_created_after_context_entered_raises() -> None:
    async with DIContext(DIRegistry("app", [cached])) as app_ctx, app_ctx.enter_nested() as req:
        with pytest.raises(DIRegistrationError, match=r"'per-call' was created after <DIContext \[open\] scope='app'"):
            req.enter_nested(DIRegistry("per-call", [cached]))


async def test_registry_created_before_any_context_entered() -> None:
    # you should be able to create registries and contexts, as long as the context
    # isn't entered
    app_ctx = DIContext(DIRegistry("app", []))
    route = DIRegistry("route", [cached])
    async with app_ctx, DIContext(route, parent=app_ctx) as req:
        assert await req.solve("cached") == 1


@pytest.mark.parametrize("scopes", [("app", "req"), ("app", "session", "request"), ("application", "req")])
async def test_nested_registries_with_differing_scope_order_raises(scopes: tuple[str, ...]) -> None:
    app_registry = DIRegistry("app", [], scopes=("app", "request"))
    async with DIContext(app_registry) as app_ctx:
        with pytest.raises(DIScopeError, match="declares scopes"):
            DIContext(DIRegistry("other", [], scopes=scopes), parent=app_ctx)
        with pytest.raises(DIScopeError, match="declares scopes"):
            app_ctx.enter_nested(DIRegistry("other", [], scopes=scopes))
        assert app_ctx._slots == {}


async def test_deep_nested_registry_mixing() -> None:
    app_registry = DIRegistry("app", [request_value])
    route = DIRegistry("route", [cached, request_value])
    async with DIContext(app_registry) as app_ctx:
        async with app_ctx.enter_nested() as req:
            first = await req.solve("request_value")
            async with DIContext(route, parent=req) as handler:  # switching below the outermost context
                assert await handler.solve("cached") == 1
                assert await handler.solve("request_value") is first  # same provider, same predecessors: one node
            async with DIContext(app_registry, parent=req) as handler:
                assert handler.registry is app_registry
        async with DIContext(route, parent=app_ctx) as req, req.enter_nested(app_registry) as handler:
            assert handler.registry is app_registry  # back to the registry the chain started from
        assert app_ctx._slots.keys() == {slot_key(route, cached)}


async def test_identical_predecessors_resolve_as_one_value() -> None:
    """Two registries that declare one provider sharing the same dependencies are the same slot"""
    calls = 0

    @provide(scope="app", key="dsn")
    async def dsn() -> str:
        nonlocal calls
        calls += 1
        return "dsn"

    @provide(scope="app")
    async def engine(dsn: NamedDependency[str]) -> str:
        return f"engine({dsn})"

    app_registry = DIRegistry("app", [engine, dsn])
    alpha = DIRegistry("alpha", [engine, dsn])
    beta = DIRegistry("beta", [engine, dsn])

    async with DIContext(app_registry) as app_ctx:
        for registry in (alpha, beta):
            async with DIContext(registry, parent=app_ctx) as req:
                assert await req.solve("engine") == "engine(dsn)"
                assert req.get("engine") == "engine(dsn)"
        assert app_ctx.get("engine") == "engine(dsn)"  # the app's own chain names the same slot
        assert calls == 1
        assert app_ctx._slots.keys() == {slot_key(alpha, engine), slot_key(alpha, dsn)}
        assert slot_key(alpha, engine) == slot_key(beta, engine) == slot_key(app_registry, engine)


async def test_divergent_predecessors_resolve_as_distinct_values() -> None:
    """
    two registries that declare one provider but not the same dependencies for that
    provider are two different graphs, and should result in two distinct values
    """
    torn_down: list[str] = []

    @provide(scope="app", key="dsn")
    async def dsn_a() -> str:
        return "a"

    @provide(scope="app", key="dsn")
    async def dsn_b() -> str:
        return "b"

    @provide(scope="app")
    async def engine(dsn: NamedDependency[str]) -> AsyncGenerator[str, None]:
        yield f"engine({dsn})"
        torn_down.append(f"engine({dsn})")

    app_registry = DIRegistry("app", [engine, dsn_a])
    alpha = DIRegistry("alpha", [engine, dsn_a])
    beta = DIRegistry("beta", [engine, dsn_b])
    assert alpha.predecessors_of(engine) == app_registry.predecessors_of(engine) != beta.predecessors_of(engine)

    async with DIContext(app_registry) as app_ctx:
        async with DIContext(alpha, parent=app_ctx) as req:
            assert await req.solve("engine") == "engine(a)"
        async with DIContext(beta, parent=app_ctx) as req:
            with pytest.raises(DIResolutionError, match="has not been resolved"):
                req.get("engine")  # alpha's value is there, under alpha's node, out of reach
            assert await req.solve("engine") == "engine(b)"
            assert req.get("engine") == "engine(b)"
        assert app_ctx.get("engine") == "engine(a)"  # the app names alpha's node
        assert app_ctx._slots.keys() == {
            slot_key(alpha, engine),
            slot_key(beta, engine),
            slot_key(alpha, dsn_a),
            slot_key(beta, dsn_b),
        }
    assert sorted(torn_down) == ["engine(a)", "engine(b)"]


async def test_predecessor_divergence_propagates_upward_only() -> None:
    """
    Overriding 'engine' gives a route its own 'session' and its own dependents of 'session';
    'cfg' beneath the override is still one value, and the route reads the very same object
    """
    cfg_calls = 0

    @provide(scope="app", key="cfg")
    async def cfg() -> str:
        nonlocal cfg_calls
        cfg_calls += 1
        return "cfg"

    async def make_engine(cfg: NamedDependency[str]) -> str:
        return f"engine({cfg})"

    @provide(scope="app")
    async def session(engine: NamedDependency[str]) -> str:
        return f"session({engine})"

    @provide(scope="app")
    async def repo(session: NamedDependency[str]) -> str:
        return f"repo({session})"

    app_engine = Provider(make_engine, kind="named", scope="app", key="engine")
    route_engine = Provider(make_engine, kind="named", scope="app", key="engine")
    app_registry = DIRegistry("app", [cfg, app_engine, session, repo])
    route = DIRegistry("route", [cfg, route_engine, session, repo])  # a merged map with 'engine' overridden

    assert route.predecessors_of(cfg) == app_registry.predecessors_of(cfg)
    assert route.predecessors_of(session) != app_registry.predecessors_of(session)
    assert route.predecessors_of(repo) != app_registry.predecessors_of(repo)

    async with DIContext(app_registry) as app_ctx:
        assert await app_ctx.solve("repo") == "repo(session(engine(cfg)))"
        async with DIContext(route, parent=app_ctx) as req:
            assert await req.solve("repo") == "repo(session(engine(cfg)))"
            assert req.get("cfg") is app_ctx.get("cfg")
            assert req.get("session") is not app_ctx.get("session")
        assert cfg_calls == 1
        assert len(app_ctx._slots) == 7  # cfg once. engine, session and repo twice each


async def test_registries_declaring_outer_key_differently_get_one_value_each() -> None:
    # two Provider objects are two distinct declarations. each chain sees the value its
    # own registry names, both live in the app context, and both are disposed when it closes
    torn_down: list[str] = []

    @provide(scope="app")
    async def cfg() -> AsyncGenerator[str, None]:
        yield "REAL"
        torn_down.append("REAL")

    @provide(scope="app", key="cfg")
    async def fake_cfg() -> AsyncGenerator[str, None]:
        yield "FAKE"
        torn_down.append("FAKE")

    @provide(scope="request")
    async def svc(cfg: NamedDependency[str]) -> str:
        return f"svc({cfg})"

    base = DIRegistry("base", [cfg, svc])
    overrides = DIRegistry("overrides", [fake_cfg, svc])

    async with DIContext(base) as app_ctx:
        async with DIContext(overrides, parent=app_ctx) as req:
            assert await req.solve("svc") == "svc(FAKE)"
        async with DIContext(base, parent=app_ctx) as req:
            assert await req.solve("svc") == "svc(REAL)"

        assert app_ctx._slots.keys() == {slot_key(base, cfg), slot_key(overrides, fake_cfg)}
        assert app_ctx.get("cfg") == "REAL"  # base's chain is unaffected by the other declaration

    assert torn_down == ["REAL", "FAKE"]  # both owned by the app context, both disposed


async def test_two_provider_instances_sharing_factory_are_distinct() -> None:
    """
    The factory identity should not influence the node's identity. Two provider
    instances sharing one factory instance should be treated as two distinct providers
    """
    built = 0
    torn_down: list[int] = []

    async def engine() -> AsyncGenerator[int, None]:
        nonlocal built
        built += 1
        mine = built
        yield mine
        torn_down.append(mine)

    app_registry = DIRegistry("app", [])
    alpha = DIRegistry("alpha", [Provider(engine, kind="named", scope="app", key="engine")])
    beta = DIRegistry("beta", [Provider(engine, kind="named", scope="app", key="engine")])

    async with DIContext(app_registry) as app_ctx:
        async with DIContext(alpha, parent=app_ctx) as req:
            assert await req.solve("engine") == 1
        async with DIContext(beta, parent=app_ctx) as req:
            assert await req.solve("engine") == 2
        assert len(app_ctx._slots) == 2

    assert torn_down == [2, 1]  # LIFO, both owned by the app context


async def test_duplicate_providers_are_invisible_below_their_scope() -> None:
    built = 0

    async def thing() -> int:
        nonlocal built
        built += 1
        return built

    app_registry = DIRegistry("app", [])
    first, second = DIRegistry("first", []), DIRegistry("second", [])
    for registry in (first, second):
        registry.register_callable(thing, key="thing", scope="request")

    assert first.get_provider("thing") is not second.get_provider("thing")

    async with DIContext(app_registry) as app_ctx:
        for registry in (first, second):
            async with DIContext(registry, parent=app_ctx) as req:
                await req.solve("thing")
        assert built == 2  # one per request, which is what request scope means
        assert app_ctx._slots == {}  # nothing landed on the shared context


async def test_provider_declared_below_its_scope_hoists_resolution_to_outer_context() -> None:
    """
    the provider scope declaration is independent of the registry. an 'app' scoped
    provider on a per-route registry should resolve through the 'app'-scoped context,
    even if that context does not know this provider
    """
    torn_down: list[str] = []
    calls = 0

    @provide(scope="app")
    async def settings() -> str:
        return "s"

    @provide(scope="app")
    async def config(settings: NamedDependency[str]) -> AsyncGenerator[str, None]:
        nonlocal calls
        calls += 1
        yield f"config({settings})"
        torn_down.append("config")

    app_registry = DIRegistry("app", [])  # 'app' entered with no providers at all
    route = DIRegistry("route", [config, settings])

    async with DIContext(app_registry) as app_ctx:
        assert app_ctx._slots == {}
        async with DIContext(route, parent=app_ctx) as first:
            assert await first.solve("config") == "config(s)"
        async with DIContext(route, parent=app_ctx) as second:
            assert await second.solve("config") == "config(s)"
        assert calls == 1  # app lifetime, not per request
        assert app_ctx._slots.keys() == {slot_key(route, config), slot_key(route, settings)}
        assert torn_down == []
    assert torn_down == ["config"]  # disposed by the context that owns it, at app shutdown


async def test_seed_shared_with_nested_registry() -> None:
    seed = Provider.seed("cfg", scope="app")
    app_registry = DIRegistry("app", [seed])
    route = DIRegistry("route", [seed])

    async with DIContext(app_registry, seeds={"cfg": "value"}) as app_ctx:
        async with DIContext(route, parent=app_ctx) as req:
            assert await req.solve("cfg") == "value"


async def test_seed_of_nested_registry_at_parent_scope_raises() -> None:
    # the route registry declares its own app scoped seed. the app context was created
    # from the app registry, which does not have it, so no value was ever given for it
    app_registry = DIRegistry("app", [])
    route = DIRegistry("route", [Provider.seed("cfg", scope="app")])

    async with DIContext(app_registry) as app_ctx:
        async with DIContext(route, parent=app_ctx) as req:
            with pytest.raises(DIResolutionError, match="'cfg' is declared as a seed and has no callable"):
                await req.solve("cfg")


async def test_seed_of_nested_registry_at_own_scope() -> None:
    app_registry = DIRegistry("app", [])
    route = DIRegistry("route", [Provider.seed("request_obj", scope="request")])

    async with DIContext(app_registry) as app_ctx:
        async with DIContext(route, parent=app_ctx, seeds={"request_obj": "value"}) as req:
            assert await req.solve("request_obj") == "value"


async def test_registry_producing_key_another_seeds_gets_own_value() -> None:
    # the app registry declares the key as a seed, the route registry has a factory for it.
    # a context of the route registry resolves the factory's value, the app context the
    # seeded one. both values are kept in the app context

    @provide(scope="app", key="settings")
    async def make_settings() -> str:
        return "made"

    seed = Provider.seed("settings", scope="app")
    app_registry = DIRegistry("app", [seed])
    route = DIRegistry("route", [make_settings])

    async with DIContext(app_registry, seeds={"settings": "seeded"}) as app_ctx:
        async with DIContext(route, parent=app_ctx) as req:
            assert await req.solve("settings") == "made"
        assert app_ctx.get("settings") == "seeded"
        assert app_ctx._slots.keys() == {slot_key(route, make_settings)}


async def test_registry_seeding_key_another_seeds_at_another_scope_gets_own_value() -> None:
    app_registry = DIRegistry("app", [Provider.seed("settings", scope="app")])
    route = DIRegistry("route", [Provider.seed("settings", scope="request")])

    async with DIContext(app_registry, seeds={"settings": "app"}) as app_ctx:
        async with DIContext(route, parent=app_ctx, seeds={"settings": "request"}) as req:
            assert req.get("settings") == "request"
        assert app_ctx.get("settings") == "app"


async def test_unknown_type_key_gets_no_name_suggestions(full_registry: DIRegistry) -> None:

    class Unknown:
        pass

    async with DIContext(full_registry) as ctx:
        with pytest.raises(MissingProviderError) as exc_info:
            await ctx.solve(Unknown)

    assert "did you mean" not in str(exc_info.value)


def test_graph_errors_render_without_registry_name() -> None:
    assert str(MissingProviderError("nope")) == "No provider is registered for dependency 'nope'."
    assert "registry:" not in str(CircularDependencyError(("a", "b", "a")))


async def test_factory_solving_own_key_raises() -> None:
    holder: dict[str, DIContext] = {}

    @provide(scope="app")
    async def itself() -> str:
        return await holder["ctx"].solve("itself")  # type: ignore[no-any-return]

    async with DIContext(DIRegistry("app", [itself])) as ctx:
        holder["ctx"] = ctx
        with pytest.raises(
            DIResolutionError, match=r"'DIContext\.solve\(\)' of.*used from inside the provider producing 'itself'"
        ):
            await ctx.solve("itself")


async def test_factory_solving_its_dependent_raises() -> None:
    holder: dict[str, DIContext] = {}

    @provide(scope="request")
    async def first() -> str:
        return await holder["ctx"].solve("second")  # type: ignore[no-any-return]

    @provide(scope="request")
    async def second() -> str:
        return await holder["ctx"].solve("first")  # type: ignore[no-any-return]

    async with DIContext(DIRegistry("app", [first, second])) as app, app.enter_nested() as request:
        holder["ctx"] = request
        with pytest.raises(
            DIResolutionError, match=r"'DIContext\.solve\(\)' of.*used from inside the provider producing 'first'"
        ):
            await request.solve("first")


async def test_factory_calling_inject_raises() -> None:
    holder: dict[str, DIContext] = {}

    async def handler(outer: NamedDependency[str]) -> str:
        return outer

    @provide(scope="request")
    async def outer(inner: NamedDependency[str]) -> str:
        return inner

    @provide(scope="request")
    async def inner() -> str:
        return await holder["ctx"].inject(handler)

    async with DIContext(DIRegistry("app", [outer, inner])) as app, app.enter_nested() as request:
        holder["ctx"] = request
        with pytest.raises(
            DIResolutionError, match=r"'DIContext\.inject\(\)' of.*used from inside the provider producing 'inner'"
        ):
            await request.inject(handler)


async def test_factory_solving_unrelated_key_raises() -> None:
    holder: dict[str, DIContext] = {}

    @provide(scope="request")
    async def derived() -> Config:
        return await holder["ctx"].solve(Config)

    async with DIContext(DIRegistry("app", [config, derived])) as app, app.enter_nested() as request:
        holder["ctx"] = request
        with pytest.raises(
            DIResolutionError, match=r"'DIContext\.solve\(\)' of.*used from inside the provider producing 'derived'"
        ):
            await request.solve("derived")

        await request.solve(Config)


async def test_get_inside_factory_reads_resolved_values() -> None:
    holder: dict[str, DIContext] = {}

    @provide(scope="request")
    async def reads() -> Config:
        return holder["ctx"].get(Config)

    @provide(scope="request")
    async def reads_itself() -> str:
        return holder["ctx"].get("reads_itself")  # type: ignore[no-any-return]

    registry = DIRegistry("app", [config, reads, reads_itself])
    async with DIContext(registry) as app, app.enter_nested() as request:
        holder["ctx"] = request
        resolved = await request.solve(Config)
        assert await request.solve("reads") is resolved

        # reads_itself does not exist before itself :)
        with pytest.raises(DIResolutionError, match="Cannot statically get 'reads_itself'"):
            await request.solve("reads_itself")


async def test_factories_solving_each_other_from_two_tasks_raise() -> None:
    """Each production reaches back for the other's key from its own task; both raise."""
    holder: dict[str, DIContext] = {}

    @provide(scope="request")
    async def left() -> str:
        await asyncio.sleep(0)  # let the other production start before reaching back
        return await holder["ctx"].solve("right")  # type: ignore[no-any-return]

    @provide(scope="request")
    async def right() -> str:
        await asyncio.sleep(0)
        return await holder["ctx"].solve("left")  # type: ignore[no-any-return]

    async with DIContext(DIRegistry("app", [left, right])) as app, app.enter_nested() as request:
        holder["ctx"] = request
        results = await asyncio.gather(request.solve("left"), request.solve("right"), return_exceptions=True)
        assert all(isinstance(result, DIResolutionError) for result in results)
        assert any("'left'" in str(r) for r in results)
        assert any("'right'" in str(r) for r in results)


async def test_task_started_by_factory_solving_during_production_raises() -> None:
    """The marker travels with the context: a child task the factory resolves through raises like
    the factory itself."""
    holder: dict[str, DIContext] = {}

    @provide(scope="request")
    async def via_child_task() -> str:
        (value,) = await asyncio.gather(holder["ctx"].solve("leaf"))
        return value  # type: ignore[no-any-return]

    @provide(scope="request")
    async def leaf() -> str:
        return "leaf"

    async with DIContext(DIRegistry("app", [via_child_task, leaf])) as app, app.enter_nested() as request:
        holder["ctx"] = request
        with pytest.raises(
            DIResolutionError,
            match=r"'DIContext\.solve\(\)' of.*used from inside the provider producing 'via_child_task'",
        ):
            await request.solve("via_child_task")


async def test_task_started_by_factory_solving_after_production_resolves() -> None:
    """A background task inherits the marker, but once the production has ended, it resolves."""
    holder: dict[str, DIContext] = {}
    release = asyncio.Event()
    background: list[asyncio.Task[str]] = []

    @provide(scope="app")
    async def starter() -> str:
        async def worker() -> str:
            await release.wait()
            return await holder["ctx"].solve("leaf")  # type: ignore[no-any-return]

        background.append(asyncio.create_task(worker()))
        return "starter"

    @provide(scope="app")
    async def leaf() -> str:
        return "leaf"

    async with DIContext(DIRegistry("app", [starter, leaf])) as ctx:
        holder["ctx"] = ctx
        assert await ctx.solve("starter") == "starter"
        release.set()
        assert await background[0] == "leaf"


async def test_handler_calling_solve_and_get_resolves() -> None:
    """An injection target runs outside any production and may use the context freely."""

    @provide(scope="request")
    async def leaf() -> str:
        return "leaf"

    async def handler(ctx: DIContext) -> str:
        return await ctx.solve("leaf") + ctx.get("leaf")  # type: ignore[no-any-return]

    async with DIContext(DIRegistry("app", [leaf])) as app, app.enter_nested() as request:
        assert await request.inject(handler, (request,)) == "leafleaf"


async def test_caller_gate_runs_once_per_entry_point(mocker: MockerFixture, resolve: Resolve) -> None:

    @provide(scope="request")
    async def leaf() -> str:
        return "leaf"

    @provide(scope="request")
    async def middle(leaf: NamedDependency[str]) -> str:
        return f"middle({leaf})"

    @provide(scope="request")
    async def top(middle: NamedDependency[str]) -> str:
        return f"top({middle})"

    spy = mocker.spy(DIContext, "_check_usable")

    async with DIContext(DIRegistry("app", [leaf, middle, top])) as app, app.enter_nested() as request:
        spy.reset_mock()
        assert await resolve(request, "top") == "top(middle(leaf))"
        assert spy.call_count == 1
        assert request.get("top") == "top(middle(leaf))"
        assert spy.call_count == 2


async def test_using_unentered_context_raises(full_registry: DIRegistry) -> None:
    ctx = DIContext(full_registry)

    with pytest.raises(DIScopeError, match="has not been entered"):
        await ctx.solve("app_value")
    with pytest.raises(DIScopeError, match="has not been entered"):
        await ctx.inject(lambda: None)
    with pytest.raises(DIScopeError, match="has not been entered"):
        ctx.get("app_value")


async def test_entering_child_before_parent_raises(full_registry: DIRegistry) -> None:
    # a child can be created before its parent is entered. entering it is what raises,
    # not the first resolution that reaches the parent
    app_ctx = DIContext(full_registry)
    request = DIContext(app_ctx.registry, scope="request", parent=app_ctx)

    with pytest.raises(DIScopeError, match="has not been entered"):
        async with request:
            pass  # pragma: no cover

    async with app_ctx, request:
        assert await request.solve("app_value") is await app_ctx.solve("app_value")


async def test_entering_child_after_parent_closed_raises(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as app_ctx:
        request = app_ctx.enter_nested()

    with pytest.raises(DIContextClosedError, match="is closed"):
        async with request:
            pass  # pragma: no cover


def test_context_built_and_seeded_without_running_loop() -> None:
    registry = DIRegistry("app", [Provider.seed("request_obj", scope="app")])
    ctx = DIContext(registry, seeds={"request_obj": "seeded"})

    async def run() -> str:
        async with ctx:
            return await ctx.solve("request_obj")  # type: ignore[no-any-return]

    assert asyncio.run(run()) == "seeded"


async def test_enter_nested_returns_child_context(full_registry: DIRegistry) -> None:
    async with DIContext(full_registry) as app_ctx:
        child = app_ctx.enter_nested()
        assert isinstance(child, DIContext)
        assert child.parent is app_ctx
        assert "not entered" in repr(child)
        async with child:
            assert await child.solve("request_value") is await child.solve("request_value")
        assert child.closed


async def test_repr_reports_state_scope_registry_and_identity(full_registry: DIRegistry) -> None:
    ctx = DIContext(full_registry)
    assert repr(ctx) == f"<DIContext [not entered] scope='app' registry='app' at {id(ctx):#x}>"
    async with ctx:
        assert repr(ctx) == f"<DIContext [open] scope='app' registry='app' at {id(ctx):#x}>"
    assert repr(ctx) == f"<DIContext [closed] scope='app' registry='app' at {id(ctx):#x}>"
