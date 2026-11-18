# pyright: reportUnnecessaryTypeIgnoreComment=false
from __future__ import annotations

import pytest

from litestar.di import (
    DIContext,
    DIRegistry,
    InjectionTarget,
    NamedDependency,
    Provider,
    ProviderKind,
    TypeDependency,
    ValueGraphDivergence,
    check_divergence,
    provide,
)
from litestar.di.exceptions import (
    CircularDependencyError,
    DIRegistrationError,
    DivergenceError,
    DivergenceWarning,
    MissingProviderError,
)
from litestar.di.provider import _DEFAULT_SCOPE
from litestar.di.registry import _DEFAULT_SCOPES


class Config:
    pass


class Database:
    pass


def make_provider(name: str, *, scope: str = "request", deps: tuple[str, ...] = ()) -> Provider:
    """Build a name-keyed provider called ``name`` depending on the named keys ``deps``."""
    parameters = ", ".join(f"{dep}: NamedDependency[int]" for dep in deps)
    # A callable belongs to a registered module, the way litestar resolves a handler's annotations.
    namespace: dict[str, object] = {"__name__": __name__, "NamedDependency": NamedDependency}
    exec(f"async def {name}({parameters}) -> int: return 1", namespace)
    return Provider(namespace[name], kind="named", scope=scope)  # type: ignore[arg-type]


def test_register_provider_instance() -> None:
    provider = make_provider("db")
    registry = DIRegistry("app", [provider])

    assert registry.get_provider("db") is provider


@pytest.mark.parametrize(
    ("key", "kind"),
    [pytest.param("db", ProviderKind.NAMED, id="string-key"), pytest.param(Database, ProviderKind.TYPE, id="type-key")],
)
def test_register_callable_infers_kind_from_key(key: str | type, kind: ProviderKind) -> None:
    async def factory() -> Database:
        return Database()

    registry = DIRegistry("app", [])
    registry.register_callable(factory, key=key)

    provider = registry.get_provider(key)
    assert provider is not None
    assert provider.kind is kind
    assert provider.key == key


def test_duplicate_key_raises() -> None:
    async def provide_db() -> Database:
        return Database()

    async def provide_other_db() -> Database:
        return Database()

    registry = DIRegistry("app", [Provider(provide_db, key="db")])
    with pytest.raises(
        DIRegistrationError,
        match=r"Cannot register provider .*\.provide_other_db \(.*\) at registry 'app' for key 'db'\. "
        r"Another provider is already registered for this key: .*\.provide_db \(.*\)\.",
    ):
        registry.register(Provider(provide_other_db, key="db"))


def test_override_replaces_provider() -> None:
    registry = DIRegistry("app", [make_provider("db")])
    replacement = make_provider("db")
    registry.register(replacement, override=True)

    assert registry.get_provider("db") is replacement


def test_get_provider_of_unknown_key_returns_none() -> None:
    assert DIRegistry("app", [make_provider("db")]).get_provider("elsewhere") is None


def test_name_and_type_keys_do_not_collide() -> None:
    async def by_name() -> Database:
        return Database()

    async def by_type() -> Database:
        return Database()

    registry = DIRegistry("app", [])
    registry.register_callable(by_name, key="Database")
    registry.register_callable(by_type, key=Database)

    assert registry.get_provider("Database") is not registry.get_provider(Database)


def test_registering_unknown_scope_raises() -> None:
    registry = DIRegistry("app", [])
    with pytest.raises(
        DIRegistrationError,
        match="Unknown scope 'nope'. Cannot register provider db with scope 'nope' on "
        "registry 'app' with declared scopes 'app' -> 'request' -> 'handler'",
    ):
        registry.register(make_provider("db", scope="nope"))


def test_scopes_default_to_app_request_handler() -> None:
    assert DIRegistry("app", []).scopes == _DEFAULT_SCOPES == ("app", "request", "handler")


def test_registries_declare_own_scopes() -> None:
    assert DIRegistry("one", [], scopes=("a", "b")).scopes == ("a", "b")
    assert DIRegistry("two", [], scopes=("c", "d")).scopes == ("c", "d")


@pytest.mark.parametrize(
    ("scopes", "message"),
    [
        pytest.param((), "empty scope order", id="empty"),
        pytest.param(("a", "b", "a"), "duplicate scopes", id="duplicate"),
    ],
)
def test_empty_or_duplicate_scope_order_raises(scopes: tuple[str, ...], message: str) -> None:
    with pytest.raises(DIRegistrationError, match=message):
        DIRegistry("app", [], scopes=scopes)


def test_static_order_is_dependency_first() -> None:
    registry = DIRegistry(
        "app",
        [
            make_provider("a", deps=("b", "c")),
            make_provider("b", deps=("d",)),
            make_provider("c", deps=("d",)),
            make_provider("d"),
        ],
    )

    registry.freeze()
    order = registry._static_order
    assert order.index("d") < order.index("b") < order.index("a")
    assert order.index("d") < order.index("c") < order.index("a")
    assert set(order) == {"a", "b", "c", "d"}


def test_missing_sub_dependency_raises_with_path_and_provider() -> None:
    registry = DIRegistry("app", [make_provider("a", deps=("b",)), make_provider("b", deps=("c",))])

    with pytest.raises(MissingProviderError) as exc_info:
        registry.freeze()

    message = str(exc_info.value)
    assert "'c'" in message
    assert "dependency path: 'a' -> 'b' -> 'c'" in message
    assert "required by:" in message
    assert exc_info.value.path == ("a", "b", "c")


def test_name_key_for_type_keyed_provider_raises_naming_type_key() -> None:
    """``config: NamedDependency[Config]`` against a provider keyed ``Config``."""

    @provide(scope="app", kind="type")
    async def config() -> Config:
        return Config()

    @provide()
    async def uses(config: NamedDependency[Config]) -> Config:
        return config

    with pytest.raises(MissingProviderError) as exc_info:
        DIRegistry("app", [config, uses]).freeze()

    message = str(exc_info.value)
    assert "but a similar provider with the type key Config was found" in message


def test_type_key_for_name_keyed_provider_raises_naming_name_key() -> None:
    @provide(scope="app")
    async def config() -> Config:
        return Config()

    @provide()
    async def uses(cfg: TypeDependency[Config]) -> Config:
        return cfg

    with pytest.raises(MissingProviderError) as exc_info:
        DIRegistry("app", [config, uses]).freeze()

    message = str(exc_info.value)
    assert "but a similar provider with the string key 'config' was found" in message


def test_check_target_with_every_required_dependency_provided() -> None:
    @provide(scope="app")
    async def db() -> Database:
        return Database()

    @provide(scope="app", kind="type")
    async def config() -> Config:
        return Config()

    async def handler(db: NamedDependency[Database], config: TypeDependency[Config]) -> None:
        pass

    DIRegistry("app", [db, config]).check_target(handler)


def test_check_target_without_provider_for_dependency_raises() -> None:
    @provide(scope="app")
    async def config() -> Config:
        return Config()

    async def handler(config: NamedDependency[Config], db: NamedDependency[Database]) -> None:
        pass

    with pytest.raises(MissingProviderError) as exc_info:
        DIRegistry("app", [config]).check_target(handler)

    message = str(exc_info.value)
    assert "Registry 'app' has no provider for dependency 'db'." in message
    assert "required by: test_check_target_without_provider_for_dependency_raises.<locals>.handler" in message
    assert exc_info.value.key == "db"


def test_check_target_optional_dependency_without_provider() -> None:
    async def handler(db: NamedDependency[Database] | None = None) -> None:
        pass

    DIRegistry("app", []).check_target(handler)


def test_check_target_optional_type_without_default_raises() -> None:
    """Only a default makes a dependency optional."""

    async def handler(db: NamedDependency[Database | None]) -> None:
        pass

    with pytest.raises(MissingProviderError, match="has no provider for dependency 'db'"):
        DIRegistry("app", []).check_target(handler)


def test_check_target_accepts_an_injection_target() -> None:
    async def handler(db: NamedDependency[Database]) -> None:
        pass

    with pytest.raises(MissingProviderError, match=r"required by: .*<locals>\.handler"):
        DIRegistry("app", []).check_target(InjectionTarget(handler))


def test_missing_provider_suggests_close_names() -> None:
    registry = DIRegistry("app", [make_provider("a", deps=("databse",)), make_provider("database")])

    with pytest.raises(MissingProviderError, match="did you mean: 'database'"):
        registry.freeze()


@pytest.mark.parametrize(
    ("graph", "cycle"),
    [
        pytest.param({"a": ("a",)}, ("a", "a"), id="self"),
        pytest.param({"a": ("b",), "b": ("c",), "c": ("a",)}, ("a", "b", "c", "a"), id="longer"),
        pytest.param({"a": (), "b": ("c",), "c": ("b",)}, ("b", "c", "b"), id="beside-an-unrelated-provider"),
    ],
)
def test_cycle_raises(graph: dict[str, tuple[str, ...]], cycle: tuple[str, ...]) -> None:
    registry = DIRegistry("app", [make_provider(name, deps=deps) for name, deps in graph.items()])

    with pytest.raises(CircularDependencyError) as exc_info:
        registry.freeze()

    assert exc_info.value.cycle == cycle
    assert " -> ".join(map(repr, cycle)) in str(exc_info.value)


def test_missing_provider_in_unused_branch_raises() -> None:
    registry = DIRegistry("app", [make_provider("a"), make_provider("b", deps=("missing",))])

    with pytest.raises(MissingProviderError, match="'missing'"):
        registry.freeze()


def test_type_keyed_graph() -> None:
    @provide(kind="type")
    async def config() -> Config:
        return Config()

    @provide(kind="type")
    async def database(cfg: TypeDependency[Config]) -> Database:
        return Database()

    registry = DIRegistry("app", [config, database])
    registry.freeze()
    assert registry._static_order == (Config, Database)


@provide(scope="app", key="greeting")
async def greeting(name: NamedDependency[str] = "world") -> str:
    return f"hello {name}"


def test_unbound_optional_dependency_not_in_static_order() -> None:
    registry = DIRegistry("app", [greeting])
    registry.freeze()
    assert registry._static_order == ("greeting",)


def test_predecessors_are_the_dependency_closure() -> None:
    """Every provider beneath a provider, as the registry binds them;
    a seed's or a leaf's are none; an optional dependency nothing binds is absent, and binding it
    names another node."""

    @provide(scope="app", key="cfg")
    async def cfg() -> str:
        return "cfg"

    @provide(scope="app", key="left")
    async def left(cfg: NamedDependency[str]) -> str:
        return f"left({cfg})"

    @provide(scope="app", key="right")
    async def right(cfg: NamedDependency[str]) -> str:
        return f"right({cfg})"

    @provide(scope="app")
    async def engine(left: NamedDependency[str], right: NamedDependency[str]) -> str:
        return f"engine({left}, {right})"

    @provide(scope="app", key="name")
    async def name() -> str:
        return "di"

    seed = Provider.seed("state", scope="app")
    registry = DIRegistry("route", [engine, left, right, cfg, seed, greeting])
    assert registry.is_frozen is False
    assert registry.predecessors_of(engine) == {left, right, cfg}
    assert registry.is_frozen is True  # asking for predecessors freezes
    assert registry.predecessors_of(left) == {cfg}  # type: ignore[unreachable]
    assert registry.predecessors_of(cfg) == frozenset()
    assert registry.predecessors_of(seed) == frozenset()
    assert registry.predecessors_of(greeting) == frozenset()  # 'name' unbound: absent

    bound = DIRegistry("bound", [greeting, name])
    assert bound.predecessors_of(greeting) == {name}
    assert bound.predecessors_of(greeting) != registry.predecessors_of(greeting)

    with pytest.raises(DIRegistrationError, match="does not declare"):
        registry.predecessors_of(name)


def test_registry_is_not_frozen_initially() -> None:
    assert DIRegistry("app", []).is_frozen is False


def test_building_context_freezes_registry() -> None:
    registry = DIRegistry("app", [make_provider("a")])
    DIContext(registry)

    assert registry.is_frozen is True


@pytest.mark.parametrize(
    ("key", "override"), [pytest.param("b", False, id="new-key"), pytest.param("a", True, id="override")]
)
def test_registering_after_freeze_raises(key: str, override: bool) -> None:
    registry = DIRegistry("app", [make_provider("a")])
    registry.freeze()

    with pytest.raises(DIRegistrationError, match="Cannot register provider at frozen registry 'app'"):
        registry.register(make_provider(key), override=override)


def test_freeze_is_idempotent() -> None:
    registry = DIRegistry("app", [make_provider("a")])
    registry.freeze()
    registry.freeze()

    assert registry.is_frozen is True


def test_freezing_is_local_to_registry() -> None:
    shared = make_provider("config")
    first = DIRegistry("first", [shared])
    second = DIRegistry("second", [shared])
    first.freeze()

    assert first.is_frozen is True
    assert second.is_frozen is False
    second.register(make_provider("extra"))  # still open


def test_failed_freeze_leaves_registry_mutable() -> None:
    registry = DIRegistry("app", [make_provider("a", deps=("b",))])

    with pytest.raises(MissingProviderError):
        registry.freeze()

    assert registry.is_frozen is False
    registry.register(make_provider("b"))
    registry.freeze()
    assert registry.is_frozen is True


def test_cycle_closed_by_override_raises_at_freeze() -> None:
    """The graph is sound until the override closes the loop."""
    sound = DIRegistry("sound", [make_provider("a", deps=("b",)), make_provider("b")])
    sound.freeze()  # sound on its own

    looped = DIRegistry("looped", [make_provider("a", deps=("b",)), make_provider("b")])
    looped.register(make_provider("b", deps=("a",)), override=True)

    with pytest.raises(CircularDependencyError, match="Circular dependency"):
        looped.freeze()


def test_one_provider_under_two_keys_raises_at_freeze() -> None:
    # 'register' cannot put a provider at a key that it doesn't own. the check is
    # there for a regression that might break this, so the map is written directly

    async def engine() -> int:
        return 1

    provider = Provider(engine, kind="named", scope="app", key="engine")
    registry = DIRegistry("app", [provider])
    registry._providers["motor"] = provider  # what a naive alias() would do

    with pytest.raises(
        DIRegistrationError,
        match="Provider key mismatch. Provider.* with key 'engine' registered for 'motor' in registry 'app'",
    ):
        registry.freeze()
    assert registry.is_frozen is False


async def make_thing() -> str:
    return "thing"


@pytest.mark.parametrize(
    "scope,expected_scope",
    [
        ("app", "app"),
        (None, _DEFAULT_SCOPE),
    ],
)
def test_register_callable_scope(scope: str | None, expected_scope: str) -> None:
    registry = DIRegistry("app", [])
    registry.register_callable(make_thing, key="thing", scope=scope)

    assert registry.get_provider("thing").scope == expected_scope  # type: ignore[union-attr]


def test_register_callable_creates_own_provider() -> None:
    # two registries handed one callable hold two distinct providers
    first = DIRegistry("first", [])
    second = DIRegistry("second", [])
    first.register_callable(make_thing, key="thing")
    second.register_callable(make_thing, key="thing")

    assert first.get_provider("thing") is not second.get_provider("thing")


def test_register_callable_passes_sync_to_thread() -> None:
    registry = DIRegistry("app", [])
    registry.register_callable(lambda: 1, key="thing", sync_to_thread=False)

    provider = registry.get_provider("thing")
    assert provider is not None
    assert provider.sync_to_thread is False


def test_repr_reports_name_size_state_and_identity() -> None:
    registry = DIRegistry("main", [make_provider("thing")])
    assert repr(registry) == f"<DIRegistry name='main' providers=1 frozen=False at {id(registry):#x}>"
    registry.freeze()
    assert repr(registry) == f"<DIRegistry name='main' providers=1 frozen=True at {id(registry):#x}>"


def test_missing_provider_path_walks_past_shared_and_optional_edges() -> None:
    """Edges into keys the walk has already seen, and optional edges nothing binds, are stepped
    over: the path still starts at an entry point and ends at the gap."""

    @provide(scope="app", key="dsn")
    async def dsn() -> str:
        return "dsn"

    @provide(scope="app")
    async def engine(
        dsn: NamedDependency[str], cache: NamedDependency[str] = "none", *, pool: NamedDependency[str]
    ) -> str:
        return f"{dsn}/{cache}/{pool}"

    @provide(scope="app")
    async def other(dsn: NamedDependency[str]) -> str:
        return dsn

    with pytest.raises(MissingProviderError) as exc_info:
        DIRegistry("app", [dsn, engine, other]).freeze()

    message = str(exc_info.value)
    assert "dependency path: 'engine' -> 'pool'" in message


def test_missing_provider_path_runs_through_requiring_provider() -> None:
    """``y`` needing ``m`` too, and closer to a root, does not put ``y`` on ``x``'s path."""
    registry = DIRegistry(
        "app",
        [make_provider("a", deps=("x",)), make_provider("x", deps=("m",)), make_provider("y", deps=("m",))],
    )

    with pytest.raises(MissingProviderError) as exc_info:
        registry.freeze()

    message = str(exc_info.value)
    assert "required by: x" in message
    assert exc_info.value.path == ("a", "x", "m")


def test_missing_provider_path_avoids_unbound_optional_edge() -> None:
    """``p`` falls back to its default for ``m``, so the path is the one to ``a2``, which requires it."""

    @provide(scope="app")
    async def r(p: NamedDependency[int]) -> int:
        return p

    @provide(scope="app")
    async def p(m: NamedDependency[int] = 0) -> int:
        return m

    @provide(scope="app")
    async def q(a1: NamedDependency[int]) -> int:
        return a1

    @provide(scope="app")
    async def a1(a2: NamedDependency[int]) -> int:
        return a2

    @provide(scope="app")
    async def a2(m: NamedDependency[int]) -> int:
        return m

    with pytest.raises(MissingProviderError) as exc_info:
        DIRegistry("app", [r, p, q, a1, a2]).freeze()

    assert exc_info.value.path == ("q", "a1", "a2", "m")


def test_registry_providers_is_read_only_view_of_every_registration() -> None:
    config = make_provider("config", scope="app")
    request = Provider.seed("request", scope="request")
    registry = DIRegistry("app", [config, request])

    providers = registry.providers
    assert dict(providers) == {"config": config, "request": request}
    assert "config" in providers
    assert registry.providers is not registry._providers

    with pytest.raises(TypeError):
        providers["other"] = make_provider("other")  # type: ignore[index]

    async def later() -> int:
        return 1

    registry.register_callable(later, key="later")
    assert "later" in providers  # a view, so registrations made before freezing show through
    assert registry.providers["later"].fn is later


def diamond(cfg_tag: str) -> tuple[DIRegistry, dict[str, Provider]]:
    """A registry with engine -> left -> cfg, where ``cfg`` is a provider of its own per call and
    ``left`` and ``engine`` are shared objects."""

    @provide(scope="app", key="cfg")
    async def cfg() -> str:
        return cfg_tag

    return DIRegistry(f"route-{cfg_tag}", [shared_engine, shared_left, cfg]), {"cfg": cfg}


@provide(scope="app", key="left")
async def shared_left(cfg: NamedDependency[str]) -> str:
    return f"left({cfg})"


@provide(scope="app", key="engine")
async def shared_engine(left: NamedDependency[str]) -> str:
    return f"engine({left})"


def test_check_divergence_raises_for_deepest_divergent_provider_first() -> None:
    """Two registries share 'engine' and 'left' and bind 'cfg' differently beneath 'left'. Walked
    dependencies first, the first finding is 'left', the deepest node that diverges; 'engine' above it
    is a finding too, and when raising never reached."""
    alpha, alpha_providers = diamond("a")
    beta, beta_providers = diamond("b")

    with pytest.raises(DivergenceError) as exc_info:
        check_divergence([alpha, beta], raise_on_divergence=True)
    finding = exc_info.value.finding
    assert finding.key == "left" and finding.provider is shared_left
    assert (finding.first_registry, finding.registry) == ("route-a", "route-b")
    assert finding.bindings == {"cfg": (alpha_providers["cfg"], beta_providers["cfg"])}

    with pytest.raises(DivergenceError) as exc_info:
        check_divergence([alpha, beta], ignore=["left"], raise_on_divergence=True)
    finding = exc_info.value.finding
    assert finding.key == "engine" and finding.provider is shared_engine
    assert finding.bindings == {"cfg": (alpha_providers["cfg"], beta_providers["cfg"])}


def test_check_divergence_identical_predecessors_are_no_finding() -> None:
    @provide(scope="app", key="cfg")
    async def cfg() -> str:
        return "cfg"

    registries = [DIRegistry(name, [shared_engine, shared_left, cfg]) for name in ("one", "two", "three")]
    check_divergence(registries, raise_on_divergence=True)
    assert all(registry.is_frozen for registry in registries)  # the check freezes


def test_check_divergence_distinct_predecessor_set_beyond_first_is_one_finding() -> None:
    """Three registries, two sets of predecessors: the second is reported once, against the first, and a
    third registry that matches either is not a finding."""
    alpha, _ = diamond("a")
    beta, _ = diamond("b")
    gamma = DIRegistry("gamma", [shared_engine, shared_left, beta.providers["cfg"]])  # the same node as beta

    with pytest.warns(DivergenceWarning) as record:
        check_divergence([alpha, beta, gamma])
    messages = [str(warning.message) for warning in record]
    assert len(messages) == 2
    assert messages[0].startswith(
        "Provider 'left' has different predecessors in registry 'route-b' than in registry 'route-a'"
    )
    assert messages[1].startswith(
        "Provider 'engine' has different predecessors in registry 'route-b' than in registry 'route-a'"
    )

    with pytest.raises(DivergenceError) as exc_info:
        check_divergence([alpha, gamma, beta], raise_on_divergence=True)
    assert exc_info.value.finding.registry == "gamma"


def test_check_divergence_covers_outermost_scope_by_default() -> None:
    """Request-scoped providers two registries bind differently are not a finding unless the scope is asked for"""

    @provide(scope="request", key="cfg")
    async def cfg_a() -> str:
        return "a"

    @provide(scope="request", key="cfg")
    async def cfg_b() -> str:
        return "b"

    @provide(scope="request")
    async def svc(cfg: NamedDependency[str]) -> str:
        return f"svc({cfg})"

    alpha = DIRegistry("alpha", [svc, cfg_a])
    beta = DIRegistry("beta", [svc, cfg_b])
    check_divergence([alpha, beta], raise_on_divergence=True)
    with pytest.warns(DivergenceWarning) as record:
        check_divergence([alpha, beta], scopes=("app", "request"))
    assert len(record) == 1
    assert str(record[0].message).startswith("Provider 'svc' has different predecessors")


def test_check_divergence_ignores_providers_by_key_and_by_provider() -> None:
    alpha, _ = diamond("a")
    beta, _ = diamond("b")

    # skip 'left' and 'engine' by key: nothing raised
    check_divergence([alpha, beta], ignore=["left", "engine"], raise_on_divergence=True)
    # skip 'left' only: 'engine' is the first finding
    with pytest.raises(DivergenceError) as exc_info:
        check_divergence([alpha, beta], ignore=["left"], raise_on_divergence=True)
    assert exc_info.value.finding.key == "engine"
    # by provider object
    with pytest.raises(DivergenceError) as exc_info:
        check_divergence([alpha, beta], ignore=[shared_left], raise_on_divergence=True)
    assert exc_info.value.finding.key == "engine"
    check_divergence([alpha, beta], ignore=[shared_left, shared_engine], raise_on_divergence=True)
    # a skipped provider is not warned about either
    with pytest.warns(DivergenceWarning) as record:
        check_divergence([alpha, beta], ignore=["left"])
    assert len(record) == 1
    assert str(record[0].message).startswith("Provider 'engine' has different predecessors")


def test_check_divergence_warns_per_finding_by_default() -> None:
    alpha, _ = diamond("a")
    beta, _ = diamond("b")
    with pytest.warns(DivergenceWarning) as record:
        check_divergence([alpha, beta])
    messages = [str(warning.message) for warning in record]
    assert len(messages) == 2
    assert messages[0].startswith(
        "Provider 'left' has different predecessors in registry 'route-b' than in registry 'route-a'"
    )
    assert messages[1].startswith(
        "Provider 'engine' has different predecessors in registry 'route-b' than in registry 'route-a'"
    )

    with pytest.raises(DivergenceError) as exc_info:
        check_divergence([alpha, beta], raise_on_divergence=True)
    assert messages[0] == str(exc_info.value.finding)


def test_check_divergence_report_names_both_registries_and_each_differing_binding() -> None:
    @provide(scope="app", key="greeting")
    async def greeting(name: NamedDependency[str] = "world") -> str:
        return f"hello {name}"

    @provide(scope="app", key="name")
    async def name() -> str:
        return "di"

    alice = DIRegistry("route", [greeting, name])
    bob = DIRegistry("route", [greeting])  # 'name' has no provider, as it's optional

    with pytest.raises(DivergenceError) as exc_info:
        check_divergence([alice, bob], raise_on_divergence=True)
    message = str(exc_info.value)
    assert (
        "Provider 'greeting' has different predecessors in registry 'route' (this registry) "
        "than in registry 'route' (a different registry with the same name). Resolution "
        "would implicitly create two distinct values for this key in the same scope ('app')" in message
    )
    assert "'name':" in message
    assert "in 'route' (this registry): <without provider>" in message
    assert "overrides=['greeting']" in message
    assert str(exc_info.value.finding) == message
    assert isinstance(exc_info.value.finding, ValueGraphDivergence)
