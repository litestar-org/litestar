# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias, cast
from unittest.mock import MagicMock

import pytest

from litestar import Controller, HttpMethod, Litestar, Request, Router, delete, get, route
from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.path_item import PathItemFactory, merge_path_item_operations
from litestar._openapi.utils import default_operation_id_creator
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Operation, PathItem, SecurityRequirement
from litestar.plugins import OpenAPISpecPlugin
from litestar.utils import find_index

if TYPE_CHECKING:
    from litestar.routes import HTTPRoute


@pytest.fixture()
def http_route(person_controller: type[Controller]) -> HTTPRoute:
    app = Litestar(route_handlers=[person_controller], openapi_config=None)
    index = find_index(app.routes, lambda x: x.path_format == "/{service_id}/person/{person_id}")
    return cast("HTTPRoute", app.routes[index])


@pytest.fixture()
def routes_with_router(person_controller: type[Controller]) -> tuple[HTTPRoute, HTTPRoute]:
    class PersonControllerV2(person_controller):  # type: ignore[misc, valid-type]
        pass

    router_v1 = Router(path="/v1", route_handlers=[person_controller])
    router_v2 = Router(path="/v2", route_handlers=[PersonControllerV2])
    app = Litestar(route_handlers=[router_v1, router_v2], openapi_config=None)
    index_v1 = find_index(app.routes, lambda x: x.path_format == "/v1/{service_id}/person/{person_id}")
    index_v2 = find_index(app.routes, lambda x: x.path_format == "/v2/{service_id}/person/{person_id}")
    return cast("HTTPRoute", app.routes[index_v1]), cast("HTTPRoute", app.routes[index_v2])


CreateFactoryFixture: TypeAlias = "Callable[[HTTPRoute], PathItemFactory]"
CreateSecurityFactoryFixture: TypeAlias = (
    "Callable[[list[SecurityRequirement] | None, tuple[OpenAPISpecPlugin, ...]], tuple[PathItemFactory, Any]]"
)


@pytest.fixture()
def create_factory() -> CreateFactoryFixture:
    def factory(route: HTTPRoute) -> PathItemFactory:
        return PathItemFactory(
            OpenAPIContext(
                openapi_config=OpenAPIConfig(title="Test", version="1.0.0", description="Test", create_examples=True),
                plugins=[],
            ),
            route,
        )

    return factory


class _StaticSpecPlugin(OpenAPISpecPlugin):
    """OpenAPISpecPlugin returning a fixed list of requirements (or ``None``).

    Accepts ``include`` / ``exclude`` so it can also exercise the path-pattern filter on the
    base class.
    """

    def __init__(
        self,
        requirements: list[SecurityRequirement] | None,
        *,
        include: str | None = None,
        exclude: str | None = None,
    ) -> None:
        super().__init__(include=include, exclude=exclude)
        self._requirements = requirements

    def get_openapi_security_requirements(self, route_handler: Any) -> list[SecurityRequirement] | None:
        return self._requirements


@pytest.fixture()
def create_security_factory() -> CreateSecurityFactoryFixture:
    """Return a builder for a ``PathItemFactory`` plus a mock route handler.

    The returned callable accepts ``handler_security`` and a tuple of ``OpenAPISpecPlugin``
    instances and returns ``(factory, handler)`` ready for ``create_security_requirements``.
    """

    def factory(
        handler_security: list[SecurityRequirement] | None,
        spec_plugins: tuple[OpenAPISpecPlugin, ...] = (),
    ) -> tuple[PathItemFactory, Any]:
        handler = MagicMock()
        handler.security = handler_security or []
        handler.paths = ("/",)

        @get("/", sync_to_thread=False)
        def _stub() -> None: ...

        app = Litestar(route_handlers=[_stub], openapi_config=None)
        index = find_index(app.routes, lambda x: x.path_format == "/")
        path_item_factory = PathItemFactory(
            OpenAPIContext(
                openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
                plugins=[],
                openapi_spec=spec_plugins,
            ),
            cast("HTTPRoute", app.routes[index]),
        )
        return path_item_factory, handler

    return factory


def test_create_path_item(http_route: HTTPRoute, create_factory: CreateFactoryFixture) -> None:
    schema = create_factory(http_route).create_path_item()
    assert schema.delete
    assert schema.delete.operation_id == "ServiceIdPersonPersonIdDeletePerson"
    assert schema.delete.summary == "DeletePerson"
    assert schema.get
    assert schema.get.operation_id == "ServiceIdPersonPersonIdGetPersonById"
    assert schema.get.summary == "GetPersonById"
    assert schema.patch
    assert schema.patch.operation_id == "ServiceIdPersonPersonIdPartialUpdatePerson"
    assert schema.patch.summary == "PartialUpdatePerson"
    assert schema.put
    assert schema.put.operation_id == "ServiceIdPersonPersonIdUpdatePerson"
    assert schema.put.summary == "UpdatePerson"


def test_unique_operation_ids_for_multiple_http_methods(create_factory: CreateFactoryFixture) -> None:
    class MultipleMethodsRouteController(Controller):
        path = "/"

        @route("/", http_method=["GET", "HEAD"])
        async def root(self, *, request: Request[str, str, Any]) -> None:
            pass

    app = Litestar(route_handlers=[MultipleMethodsRouteController], openapi_config=None)
    index = find_index(app.routes, lambda x: x.path_format == "/")
    route_with_multiple_methods = cast("HTTPRoute", app.routes[index])
    schema = create_factory(route_with_multiple_methods).create_path_item()
    assert schema.get
    assert schema.get.operation_id
    assert schema.head
    assert schema.head.operation_id
    assert schema.get.operation_id != schema.head.operation_id


def test_unique_operation_ids_for_multiple_http_methods_with_handler_level_operation_creator(
    create_factory: CreateFactoryFixture,
) -> None:
    class MultipleMethodsRouteController(Controller):
        path = "/"

        @route("/", http_method=["GET", "HEAD"], operation_id=default_operation_id_creator)
        async def root(self, *, request: Request[str, str, Any]) -> None:
            pass

    app = Litestar(route_handlers=[MultipleMethodsRouteController], openapi_config=None)
    index = find_index(app.routes, lambda x: x.path_format == "/")
    route_with_multiple_methods = cast("HTTPRoute", app.routes[index])
    factory = create_factory(route_with_multiple_methods)
    factory.context.openapi_config.operation_id_creator = lambda x: "abc"  # type: ignore[assignment, misc]
    schema = create_factory(route_with_multiple_methods).create_path_item()
    assert schema.get
    assert schema.get.operation_id
    assert schema.head
    assert schema.head.operation_id
    assert schema.get.operation_id != schema.head.operation_id


def test_routes_with_different_paths_should_generate_unique_operation_ids(
    routes_with_router: tuple[HTTPRoute, HTTPRoute], create_factory: CreateFactoryFixture
) -> None:
    route_v1, route_v2 = routes_with_router
    schema_v1 = create_factory(route_v1).create_path_item()
    schema_v2 = create_factory(route_v2).create_path_item()
    assert schema_v1.get
    assert schema_v2.get
    assert schema_v1.get.operation_id != schema_v2.get.operation_id


def test_create_path_item_use_handler_docstring_false(
    http_route: HTTPRoute, create_factory: CreateFactoryFixture
) -> None:
    factory = create_factory(http_route)
    assert not factory.context.openapi_config.use_handler_docstrings
    schema = factory.create_path_item()
    assert schema.get
    assert schema.get.description is None
    assert schema.patch
    assert schema.patch.description == "Description in decorator"


def test_create_path_item_use_handler_docstring_true(
    http_route: HTTPRoute, create_factory: CreateFactoryFixture
) -> None:
    factory = create_factory(http_route)
    factory.context.openapi_config.use_handler_docstrings = True
    schema = factory.create_path_item()
    assert schema.get
    assert schema.get.description == "Description in docstring."
    assert schema.patch
    assert schema.patch.description == "Description in decorator"
    assert schema.put
    assert schema.put.description
    # make sure multiline docstring is fully included
    assert "Line 3." in schema.put.description
    # make sure internal docstring indentation used to line up with the code
    # is removed from description
    assert "    " not in schema.put.description


def test_operation_id_validation() -> None:
    @get(path="/1", operation_id="handler")
    def handler_1() -> None: ...

    @get(path="/2", operation_id="handler")
    def handler_2() -> None: ...

    app = Litestar(route_handlers=[handler_1, handler_2])

    with pytest.raises(ImproperlyConfiguredException):
        app.openapi_schema


def test_operation_override() -> None:
    @dataclass
    class CustomOperation(Operation):
        x_code_samples: list[dict[str, str]] | None = field(default=None, metadata={"alias": "x-codeSamples"})

        def __post_init__(self) -> None:
            self.tags = ["test"]
            self.description = "test"
            self.x_code_samples = [
                {"lang": "Python", "source": "import requests; requests.get('localhost/example')", "label": "Python"},
                {"lang": "cURL", "source": "curl -XGET localhost/example", "label": "curl"},
            ]

    @get(path="/1")
    def handler_1() -> None: ...

    @get(path="/2", operation_class=CustomOperation)
    def handler_2() -> None: ...

    app = Litestar(route_handlers=[handler_1, handler_2])

    assert app.openapi_schema.paths
    assert app.openapi_schema.paths["/1"]
    assert app.openapi_schema.paths["/1"].get
    assert isinstance(app.openapi_schema.paths["/1"].get, Operation)
    assert app.openapi_schema.paths["/2"]
    assert app.openapi_schema.paths["/2"].get
    assert isinstance(app.openapi_schema.paths["/2"].get, CustomOperation)
    assert app.openapi_schema.paths["/2"].get.tags == ["test"]
    assert app.openapi_schema.paths["/2"].get.description == "test"

    operation_schema = CustomOperation().to_schema()
    assert "x-codeSamples" in operation_schema


def test_handler_excluded_from_schema(create_factory: CreateFactoryFixture) -> None:
    @get("/", sync_to_thread=False)
    def handler_1() -> None: ...

    @delete("/", include_in_schema=False, sync_to_thread=False)
    def handler_2() -> None: ...

    app = Litestar(route_handlers=[handler_1, handler_2])
    index = find_index(app.routes, lambda x: x.path_format == "/")
    route_with_multiple_methods = cast("HTTPRoute", app.routes[index])
    factory = create_factory(route_with_multiple_methods)
    schema = factory.create_path_item()
    assert schema.get
    assert schema.delete is None


@pytest.mark.parametrize("method", HttpMethod)
def test_merge_path_item_operations_operation_set_on_both_raises(method: HttpMethod) -> None:
    with pytest.raises(ValueError, match="Cannot merge operation"):
        merge_path_item_operations(
            PathItem(**{method.value.lower(): MagicMock()}),
            PathItem(**{method.value.lower(): MagicMock()}),
            for_path="/",
        )


@pytest.mark.parametrize(
    "attr",
    [
        f.name
        for f in dataclasses.fields(PathItem)
        if f.name.upper()
        not in [
            *HttpMethod,
            "TRACE",  # remove once https://github.com/litestar-org/litestar/pull/3294 is merged
        ]
    ],
)
def test_merge_path_item_operation_differing_values_raises(attr: str) -> None:
    with pytest.raises(ImproperlyConfiguredException, match="Conflicting OpenAPI path configuration for '/'"):
        merge_path_item_operations(PathItem(), PathItem(**{attr: MagicMock()}), for_path="/")


# ---------------------------------------------------------------------------
# create_security_requirements: per-operation contributions from OpenAPISpecPlugin
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("handler_security", "plugin_returns", "expected"),
    [
        # No handler security and no plugin contributions -> None (preserves prior behavior).
        ([], [], None),
        # Handler-level security alone is returned verbatim.
        ([{"A": []}], [], [{"A": []}]),
        # A single plugin contributing [B] appends after handler [A].
        ([{"A": []}], [[{"B": ["scope:b"]}]], [{"A": []}, {"B": ["scope:b"]}]),
        # Multiple plugins extend in registration order.
        (
            [{"A": []}],
            [[{"B": ["scope:b"]}], [{"C": []}]],
            [{"A": []}, {"B": ["scope:b"]}, {"C": []}],
        ),
        # A plugin returning ``None`` contributes nothing.
        ([{"A": []}], [None, [{"B": ["scope:b"]}]], [{"A": []}, {"B": ["scope:b"]}]),
        # Plugins can contribute when the handler has no own security.
        ([], [[{"B": ["scope:b"]}]], [{"B": ["scope:b"]}]),
    ],
    ids=[
        "no-security-no-plugins",
        "handler-only",
        "handler-plus-one-plugin",
        "handler-plus-two-plugins-ordered",
        "plugin-returning-none-skipped",
        "plugin-only-no-handler-security",
    ],
)
def test_create_security_requirements(
    handler_security: list[SecurityRequirement],
    plugin_returns: list[list[SecurityRequirement] | None],
    expected: list[SecurityRequirement] | None,
    create_security_factory: CreateSecurityFactoryFixture,
) -> None:
    plugins = tuple(_StaticSpecPlugin(r) for r in plugin_returns)
    factory, handler = create_security_factory(handler_security, plugins)

    assert factory.create_security_requirements(handler) == expected


@pytest.mark.parametrize(
    ("handler_paths", "include", "exclude", "should_apply"),
    [
        # No filter -> applies everywhere.
        (("/items",), None, None, True),
        # include matches one of the handler's paths -> applies.
        (("/items",), r"^/items", None, True),
        # include does NOT match -> filter rejects.
        (("/health",), r"^/items", None, False),
        # exclude matches -> filter rejects, even if include also matches.
        (("/items",), r"^/items", r"^/items", False),
        # exclude only, no match -> applies.
        (("/items",), None, r"^/health", True),
        # Iterable of patterns is supported (joined by alternation).
        (("/health",), None, [r"^/health", r"^/internal"], False),
    ],
    ids=[
        "no-filter",
        "include-match",
        "include-miss",
        "exclude-trumps-include",
        "exclude-no-match",
        "exclude-iterable",
    ],
)
def test_openapi_spec_plugin_applies_to_default_filter(
    handler_paths: tuple[str, ...],
    include: str | list[str] | None,
    exclude: str | list[str] | None,
    should_apply: bool,
) -> None:
    """The base ``applies_to`` honors include/exclude path patterns; exclude takes precedence."""
    plugin = _StaticSpecPlugin([{"X": []}], include=include, exclude=exclude)  # type: ignore[arg-type]
    handler = MagicMock()
    handler.paths = handler_paths

    assert plugin.applies_to(handler) is should_apply


def test_openapi_spec_plugin_applies_to_filter_skips_security_contribution(
    create_security_factory: CreateSecurityFactoryFixture,
) -> None:
    """When ``applies_to`` returns ``False``, the plugin's security contribution is skipped."""
    plugin = _StaticSpecPlugin([{"X": []}], exclude=r"^/$")
    factory, handler = create_security_factory(None, (plugin,))
    # The fixture builds the handler with paths == ("/",), which the exclude pattern rejects.
    assert factory.create_security_requirements(handler) is None


def test_openapi_spec_plugin_applies_to_subclass_override_for_per_route_filter() -> None:
    """A subclass can override ``applies_to`` to filter by tag/opt without writing path regex."""

    class TaggedOnlyPlugin(OpenAPISpecPlugin):
        def applies_to(self, route_handler: Any) -> bool:
            return "metered" in (route_handler.tags or ())

        def get_openapi_security_requirements(self, route_handler: Any) -> list[SecurityRequirement]:
            return [{"X-Quota": []}]

    @get("/free", sync_to_thread=False)
    def free_endpoint() -> None: ...

    @get("/paid", sync_to_thread=False, tags=["metered"])
    def paid_endpoint() -> None: ...

    app = Litestar(
        route_handlers=[free_endpoint, paid_endpoint],
        plugins=[TaggedOnlyPlugin()],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    paths = app.openapi_schema.paths
    assert paths is not None
    free_op = paths["/free"].get
    paid_op = paths["/paid"].get
    assert free_op is not None
    assert paid_op is not None
    assert free_op.security is None
    assert paid_op.security == [{"X-Quota": []}]


def test_openapi_spec_plugin_security_appears_on_operation_in_document() -> None:
    """End-to-end: a plugin's security requirements appear on the operation in the served document."""

    class StaticRequirementPlugin(OpenAPISpecPlugin):
        def get_openapi_security_requirements(self, route_handler: Any) -> list[SecurityRequirement]:
            return [{"X-Quota": []}]

    @get("/items", sync_to_thread=False)
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[StaticRequirementPlugin()],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.security == [{"X-Quota": []}]


def test_openapi_spec_plugin_include_exclude_filters_routes_in_document() -> None:
    """End-to-end: ``include``/``exclude`` patterns filter which routes a plugin contributes to."""

    class GlobalQuotaPlugin(OpenAPISpecPlugin):
        def get_openapi_security_requirements(self, route_handler: Any) -> list[SecurityRequirement]:
            return [{"X-Quota": []}]

    class AdminQuotaPlugin(OpenAPISpecPlugin):
        def get_openapi_security_requirements(self, route_handler: Any) -> list[SecurityRequirement]:
            return [{"X-Quota": ["admin"]}]

    @get("/items", sync_to_thread=False)
    def list_items() -> list[str]:
        return []

    @get("/admin/items", sync_to_thread=False)
    def list_admin_items() -> list[str]:
        return []

    @get("/health", sync_to_thread=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app = Litestar(
        route_handlers=[list_items, list_admin_items, health],
        plugins=[
            # Applies to everything except `/health`.
            GlobalQuotaPlugin(exclude=r"^/health$"),
            # Layers an extra requirement only on `/admin/*`.
            AdminQuotaPlugin(include=r"^/admin"),
        ],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    paths = app.openapi_schema.paths
    assert paths is not None

    items_op = paths["/items"].get
    admin_op = paths["/admin/items"].get
    health_op = paths["/health"].get
    assert items_op is not None
    assert admin_op is not None
    assert health_op is not None

    # `/items`: GlobalQuotaPlugin includes; AdminQuotaPlugin excludes.
    assert items_op.security == [{"X-Quota": []}]
    # `/admin/items`: both apply, in registration order.
    assert admin_op.security == [{"X-Quota": []}, {"X-Quota": ["admin"]}]
    # `/health`: GlobalQuotaPlugin excluded; AdminQuotaPlugin's include misses.
    assert health_op.security is None
