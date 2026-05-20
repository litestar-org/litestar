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
from litestar._openapi.path_item import PathItemFactory, merge_openapi_operation, merge_path_item_operations
from litestar._openapi.utils import default_operation_id_creator
from litestar.exceptions import ImproperlyConfiguredException, NotFoundException
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import (
    Operation,
    Parameter,
    PathItem,
    Reference,
)
from litestar.openapi.spec.response import OpenAPIResponse
from litestar.plugins import OpenAPISpecPlugin
from litestar.utils import find_index

if TYPE_CHECKING:
    from litestar.handlers.http_handlers import HTTPRouteHandler
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


class _OperationContributor(OpenAPISpecPlugin):
    """Test plugin that returns a fixed :class:`Operation` fragment (or ``None``)."""

    def __init__(self, fragment: Operation | None) -> None:
        self._fragment = fragment

    def get_openapi_operation(self, route_handler: Any) -> Operation | None:
        return self._fragment


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
# OpenAPISpecPlugin generic shape
# ---------------------------------------------------------------------------


def test_openapi_spec_plugin_no_init_args_required() -> None:
    """Bare ``OpenAPISpecPlugin()`` instantiates without arguments and returns ``None`` from both hooks."""
    plugin = OpenAPISpecPlugin()
    assert plugin.get_openapi_components() is None
    assert plugin.get_openapi_operation(MagicMock()) is None


def test_openapi_spec_plugin_slots_empty() -> None:
    """The base class declares ``__slots__ = ()`` (subclasses are free to define their own state)."""
    assert OpenAPISpecPlugin.__slots__ == ()


# ---------------------------------------------------------------------------
# merge_openapi_operation: per-operation merge contract
# ---------------------------------------------------------------------------


def test_merge_openapi_operation_security_extends_in_order() -> None:
    target = Operation(security=[{"A": []}])
    source = Operation(security=[{"B": ["scope:b"]}])

    merge_openapi_operation(target, source, source_label="P1")

    assert target.security == [{"A": []}, {"B": ["scope:b"]}]


def test_merge_openapi_operation_security_into_unset_target() -> None:
    target = Operation()
    source = Operation(security=[{"B": ["scope:b"]}])

    merge_openapi_operation(target, source, source_label="P1")

    assert target.security == [{"B": ["scope:b"]}]


def test_merge_openapi_operation_tags_extend_dedup_preserve_order() -> None:
    target = Operation(tags=["bar"])
    source = Operation(tags=["bar", "foo"])

    merge_openapi_operation(target, source, source_label="P1")

    assert target.tags == ["bar", "foo"]


def test_merge_openapi_operation_parameters_collide_on_name_and_location_raises() -> None:
    target = Operation(parameters=[Parameter(name="x", param_in="query")])
    source = Operation(parameters=[Parameter(name="x", param_in="query")])

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        merge_openapi_operation(target, source, source_label="DupParam")

    message = str(exc_info.value)
    assert "parameters" in message
    assert "DupParam" in message
    assert "'x'" in message
    assert "'query'" in message


def test_merge_openapi_operation_parameters_distinct_keys_extend() -> None:
    target = Operation(parameters=[Parameter(name="x", param_in="query")])
    source = Operation(parameters=[Parameter(name="x", param_in="header")])

    merge_openapi_operation(target, source, source_label="P1")

    assert target.parameters is not None
    assert len(target.parameters) == 2


def test_merge_openapi_operation_callbacks_disjoint_keys_merge() -> None:
    target = Operation(callbacks={"a": Reference(ref="#/components/callbacks/a")})
    source = Operation(callbacks={"b": Reference(ref="#/components/callbacks/b")})

    merge_openapi_operation(target, source, source_label="P1")

    assert target.callbacks is not None
    assert set(target.callbacks.keys()) == {"a", "b"}


def test_merge_openapi_operation_callbacks_collision_raises() -> None:
    target = Operation(callbacks={"shared": Reference(ref="#/x")})
    source = Operation(callbacks={"shared": Reference(ref="#/y")})

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        merge_openapi_operation(target, source, source_label="DupCallback")

    assert "callbacks" in str(exc_info.value)
    assert "'shared'" in str(exc_info.value)
    assert "DupCallback" in str(exc_info.value)


def test_merge_openapi_operation_responses_disjoint_status_codes_merge() -> None:
    target = Operation(responses={"200": OpenAPIResponse(description="ok")})
    source = Operation(responses={"503": OpenAPIResponse(description="unavailable")})

    merge_openapi_operation(target, source, source_label="P1")

    assert target.responses is not None
    assert set(target.responses.keys()) == {"200", "503"}


def test_merge_openapi_operation_responses_status_code_collision_raises() -> None:
    target = Operation(responses={"404": OpenAPIResponse(description="from handler")})
    source = Operation(responses={"404": OpenAPIResponse(description="from plugin")})

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        merge_openapi_operation(target, source, source_label="ProblemPlugin")

    message = str(exc_info.value)
    assert "responses" in message
    assert "'404'" in message
    assert "ProblemPlugin" in message


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("operation_id", "x"),
        ("summary", "x"),
        ("description", "x"),
        ("request_body", Reference(ref="#/x")),
        ("deprecated", True),
        ("external_docs", MagicMock()),
    ],
)
def test_merge_openapi_operation_forbidden_fields_raise(field_name: str, value: Any) -> None:
    target = Operation()
    source = Operation(**{field_name: value})

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        merge_openapi_operation(target, source, source_label="BadPlugin")

    assert field_name in str(exc_info.value)
    assert "BadPlugin" in str(exc_info.value)


def test_merge_openapi_operation_none_source_fields_skipped() -> None:
    """Empty/None source fields don't overwrite populated target fields."""
    target = Operation(security=[{"A": []}], tags=["existing"])
    source = Operation()

    merge_openapi_operation(target, source, source_label="EmptyPlugin")

    assert target.security == [{"A": []}]
    assert target.tags == ["existing"]


# ---------------------------------------------------------------------------
# Plugin contributions wired through PathItemFactory / OpenAPI build
# ---------------------------------------------------------------------------


def test_handler_security_alone_appears_on_operation() -> None:
    """When no plugins contribute, ``handler.security`` becomes the operation's security."""

    @get("/items", sync_to_thread=False, security=[{"A": []}])
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.security == [{"A": []}]


def test_handler_without_security_and_no_plugins_yields_none() -> None:
    @get("/items", sync_to_thread=False)
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.security is None


def test_plugin_security_appended_after_handler_security() -> None:
    plugin = _OperationContributor(Operation(security=[{"B": ["scope:b"]}]))

    @get("/items", sync_to_thread=False, security=[{"A": []}])
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[plugin],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.security == [{"A": []}, {"B": ["scope:b"]}]


def test_multiple_plugins_extend_security_in_registration_order() -> None:
    p1 = _OperationContributor(Operation(security=[{"B": ["scope:b"]}]))
    p2 = _OperationContributor(Operation(security=[{"C": []}]))

    @get("/items", sync_to_thread=False, security=[{"A": []}])
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[p1, p2],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.security == [{"A": []}, {"B": ["scope:b"]}, {"C": []}]


def test_plugin_returning_none_contributes_nothing() -> None:
    plugin = _OperationContributor(None)

    @get("/items", sync_to_thread=False, security=[{"A": []}])
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[plugin],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.security == [{"A": []}]


def test_plugin_can_filter_per_route_via_route_handler_inspection() -> None:
    """Plugins are global; per-route filtering is done by inspecting ``route_handler`` itself."""

    class TaggedOnlyPlugin(OpenAPISpecPlugin):
        def get_openapi_operation(self, route_handler: Any) -> Operation | None:
            if "metered" not in (route_handler.tags or ()):
                return None
            return Operation(security=[{"X-Quota": []}])

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


def test_plugin_contributes_tags_extending_handler_tags() -> None:
    plugin = _OperationContributor(Operation(tags=["plugin-tag"]))

    @get("/items", sync_to_thread=False, tags=["handler-tag"])
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[plugin],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.tags is not None
    # Order: handler tags first (sorted), then plugin tags appended dedup.
    assert "handler-tag" in operation.tags
    assert "plugin-tag" in operation.tags


def test_plugin_contributes_response_for_undeclared_status_code() -> None:
    """The upstream answer to #2416 / #3020 / #3021 / #4003 / #4523: plugins can contribute responses."""
    plugin = _OperationContributor(
        Operation(responses={"503": OpenAPIResponse(description="Service unavailable")}),
    )

    @get("/items", sync_to_thread=False)
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[plugin],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.responses is not None
    assert "503" in operation.responses


def test_plugin_response_overrides_default_for_handler_raises_status_code() -> None:
    """Pre-pass orchestration: plugin claim on a status code pre-empts the default handler-raises emission.

    This is the Revision 3 contract — the returned ``Operation`` fragment IS the plugin's claim.
    Handler ``raises=[NotFoundException]`` would normally emit a default ``"404"`` schema; when a
    plugin returns ``Operation(responses={"404": ...})``, the pre-pass adds ``"404"`` to
    ``plugin_owned_status_codes``, ``ResponseFactory`` skips the default emission, and the
    plugin's response lands in the operation without any collision.
    """
    plugin_response = OpenAPIResponse(description="custom not-found")
    plugin = _OperationContributor(Operation(responses={"404": plugin_response}))

    @get("/items", sync_to_thread=False, raises=[NotFoundException])
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[plugin],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    operation = app.openapi_schema.paths["/items"].get  # type: ignore[index]
    assert operation is not None
    assert operation.responses is not None
    assert "404" in operation.responses
    # The plugin's response wins; the default `create_error_responses` shape (with ``content``) is gone.
    assert operation.responses["404"] is plugin_response


def test_plugin_get_openapi_operation_called_once_per_operation() -> None:
    """The pre-pass invokes each plugin's ``get_openapi_operation`` exactly once per operation.

    Counter-instrumented: with one plugin and one handler, the count is 1. The single invocation
    feeds both the ``plugin_owned_status_codes`` pre-pass and the merge phase — the fragment is
    cached, not re-fetched.
    """

    class CountingPlugin(OpenAPISpecPlugin):
        __slots__ = ("calls",)

        def __init__(self) -> None:
            self.calls = 0

        def get_openapi_operation(self, route_handler: HTTPRouteHandler) -> Operation | None:
            self.calls += 1
            return Operation(security=[{"X-Quota": []}])

    plugin = CountingPlugin()

    @get("/items", sync_to_thread=False)
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[plugin],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    _ = app.openapi_schema  # trigger build
    assert plugin.calls == 1


def test_two_plugins_each_called_once_per_operation_in_pre_pass() -> None:
    """With two plugins, the pre-pass calls each one exactly once per operation."""

    class CountingPlugin(OpenAPISpecPlugin):
        __slots__ = ("calls",)

        def __init__(self) -> None:
            self.calls = 0

        def get_openapi_operation(self, route_handler: HTTPRouteHandler) -> Operation | None:
            self.calls += 1
            return None

    p1, p2 = CountingPlugin(), CountingPlugin()

    @get("/items", sync_to_thread=False)
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[p1, p2],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    _ = app.openapi_schema
    assert p1.calls == 1
    assert p2.calls == 1


def test_two_plugins_colliding_on_same_status_code_raises() -> None:
    p1 = _OperationContributor(Operation(responses={"503": OpenAPIResponse(description="a")}))
    p2 = _OperationContributor(Operation(responses={"503": OpenAPIResponse(description="b")}))

    @get("/items", sync_to_thread=False)
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[p1, p2],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        app.openapi_schema

    assert "'503'" in str(exc_info.value)


def test_plugin_setting_forbidden_field_raises_from_app_build() -> None:
    plugin = _OperationContributor(Operation(operation_id="x"))

    @get("/items", sync_to_thread=False)
    def list_items() -> list[str]:
        return []

    app = Litestar(
        route_handlers=[list_items],
        plugins=[plugin],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        app.openapi_schema

    assert "operation_id" in str(exc_info.value)
