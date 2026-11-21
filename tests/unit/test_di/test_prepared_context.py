from __future__ import annotations

import pytest

from litestar.di import DIContext, DIRegistry, PreparedDIContext, Provider, provide
from litestar.di.exceptions import DIScopeError


@provide(scope="request")
async def request_value() -> object:
    return object()


def test_prepared_context_defaults_to_outermost_scope() -> None:
    assert PreparedDIContext(DIRegistry("app", [])).scope == "app"


def test_nested_prepared_context_defaults_to_next_scope() -> None:
    registry = DIRegistry("app", [])

    prepared_request = PreparedDIContext(registry, parent=PreparedDIContext(registry))

    assert prepared_request.scope == "request"
    assert PreparedDIContext(registry, parent=prepared_request).scope == "handler"


async def test_prepared_context_nested_in_context_defaults_to_next_scope() -> None:
    registry = DIRegistry("app", [])

    async with DIContext(registry) as app_context:
        assert PreparedDIContext(registry, parent=app_context).scope == "request"


def test_prepared_context_freezes_registry() -> None:
    registry = DIRegistry("app", [])

    PreparedDIContext(registry)

    assert registry.is_frozen


def test_prepared_root_context_with_non_root_scope_raises() -> None:
    with pytest.raises(DIScopeError, match="has to use the outermost scope 'app'"):
        PreparedDIContext(DIRegistry("app", []), scope="request")


def test_prepared_context_unknown_scope_raises() -> None:
    with pytest.raises(DIScopeError, match="has no scope 'nope'"):
        PreparedDIContext(DIRegistry("app", []), scope="nope")


@pytest.mark.parametrize("scope", [pytest.param("handler", id="skipping"), pytest.param("app", id="repeating")])
def test_prepared_context_scope_out_of_order_raises(scope: str) -> None:
    registry = DIRegistry("app", [])

    with pytest.raises(
        DIScopeError, match=f"Cannot enter scope '{scope}' out of order. '{scope}' does not directly follow 'app'"
    ):
        PreparedDIContext(registry, scope=scope, parent=PreparedDIContext(registry))


def test_prepared_context_below_innermost_scope_raises() -> None:
    registry = DIRegistry("app", [], scopes=("app",))

    with pytest.raises(DIScopeError, match="is the innermost scope"):
        PreparedDIContext(registry, parent=PreparedDIContext(registry))


def test_prepared_context_with_scopes_other_than_parent_raises() -> None:
    parent = PreparedDIContext(DIRegistry("app", [], scopes=("process", "request")))

    with pytest.raises(
        DIScopeError,
        match="Cannot nest a context resolving through registry 'handler' inside "
        "<PreparedDIContext scope='process' registry='app'>",
    ):
        PreparedDIContext(DIRegistry("handler", []), parent=parent)


async def test_prepared_context_creates_context_of_registry_at_scope() -> None:
    app_registry = DIRegistry("app", [])
    registry = DIRegistry("handler", [request_value])
    prepared = PreparedDIContext(registry, parent=PreparedDIContext(app_registry))

    async with DIContext(app_registry) as app_context:
        async with prepared.create(app_context) as request_context:
            assert request_context.registry is registry
            assert request_context.scope == "request"
            assert request_context.parent is app_context
            value = await request_context.solve("request_value")
            assert request_context.get("request_value") is value


async def test_context_of_prepared_context() -> None:
    registry = DIRegistry("app", [request_value])
    prepared = PreparedDIContext(registry, parent=PreparedDIContext(registry))

    async with DIContext(registry) as app_context:
        async with DIContext(registry, parent=app_context, prepared=prepared) as request_context:
            assert request_context.scope == "request"
            assert request_context.parent is app_context
            value = await request_context.solve("request_value")
            assert request_context.get("request_value") is value


async def test_created_context_reads_own_seeds_and_seeds_of_parent() -> None:
    registry = DIRegistry("app", [Provider.seed("config", scope="app"), Provider.seed("user", scope="request")])
    prepared_app = PreparedDIContext(registry)
    prepared_request = PreparedDIContext(registry, parent=prepared_app)

    async with prepared_app.create(seeds={"config": 1}) as app_context:
        async with prepared_request.create(app_context, {"user": 2}) as request_context:
            assert await request_context.solve_many("config", "user") == (1, 2)


async def test_context_nests_in_created_context() -> None:
    registry = DIRegistry("app", [request_value])
    prepared_app = PreparedDIContext(registry)
    prepared_request = PreparedDIContext(registry, parent=prepared_app)

    async with prepared_app.create() as app_context:
        async with prepared_request.create(app_context) as request_context:
            async with request_context.enter_nested() as handler_context:
                assert handler_context.scope == "handler"
                assert await handler_context.solve("request_value") is request_context.get("request_value")
