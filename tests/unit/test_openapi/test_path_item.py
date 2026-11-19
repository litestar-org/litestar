# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias, cast
from unittest.mock import MagicMock

import pytest

from litestar import Controller, HttpMethod, Litestar, Request, Router, delete, get, head, post, route
from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.path_item import PathItemFactory, merge_path_item_operations
from litestar._openapi.utils import default_operation_id_creator
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Operation, PathItem
from litestar.params import FromPath, FromQuery
from litestar.testing import create_test_client
from litestar.utils import find_index
from tests.unit.test_openapi.utils import build_document

if TYPE_CHECKING:
    from litestar.handlers import HTTPRouteHandler
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
            "QUERY",
        ]
    ],
)
def test_merge_path_item_operation_differing_values_raises(attr: str) -> None:
    with pytest.raises(ImproperlyConfiguredException, match="Conflicting OpenAPI path configuration for '/'"):
        merge_path_item_operations(PathItem(), PathItem(**{attr: MagicMock()}), for_path="/")


@get("/items/{item_id:int}")
async def item_by_id(item_id: FromPath[int]) -> int:
    return item_id


@get("/items/{name:str}")
async def item_by_name(name: FromPath[str]) -> str:
    return name


@route("/items/{item_id:int}", http_method=["GET", "POST"])
async def get_or_create_item(item_id: FromPath[int]) -> None:
    return None


@post("/items/{item_id:str}")
async def create_item(item_id: FromPath[str]) -> None:
    return None


@pytest.mark.parametrize(
    "handlers, message",
    [
        ((item_by_id, item_by_name), "registered as '/items/{item_id:int}' and '/items/{name:str}'"),
        ((get_or_create_item, create_item), "both serve POST on paths"),
    ],
    ids=["parameter-names", "multi-method-handler"],
)
def test_same_method_on_paths_differing_only_in_path_parameters_raises(
    handlers: tuple[HTTPRouteHandler, HTTPRouteHandler], message: str
) -> None:
    with pytest.raises(ImproperlyConfiguredException, match=re.escape(message)):
        build_document(*handlers)


def test_different_methods_on_same_path_template_are_documented() -> None:
    @head("/items/{item_id:int}")
    async def by_int(item_id: FromPath[int]) -> None:
        return None

    @post("/items/{item_id:str}")
    async def by_str(item_id: FromPath[str]) -> None:
        return None

    paths = build_document(by_int, by_str)["paths"]

    assert list(paths) == ["/items/{item_id}"]
    assert sorted(paths["/items/{item_id}"]) == ["head", "post"]


@pytest.mark.parametrize("reverse", [False, True], ids=["registered-in-order", "registered-reversed"])
def test_different_methods_on_paths_differing_in_parameter_names_share_one_path(reverse: bool) -> None:
    @get("/things/{b:int}/parts/{part:str}")
    async def read_thing(b: FromPath[int], part: FromPath[str], limit: FromQuery[int] = 1) -> None:
        return None

    @post("/things/{a:int}/parts/{c:str}")
    async def create_thing(a: FromPath[int], c: FromPath[str]) -> None:
        return None

    handlers = [create_thing, read_thing][:: -1 if reverse else 1]
    paths = build_document(*handlers)["paths"]

    assert list(paths) == ["/things/{a}/parts/{c}"]
    assert [(p["name"], p["in"]) for p in paths["/things/{a}/parts/{c}"]["get"]["parameters"]] == [
        ("a", "path"),
        ("c", "path"),
        ("limit", "query"),
    ]
    assert [p["name"] for p in paths["/things/{a}/parts/{c}"]["post"]["parameters"]] == ["a", "c"]


def test_one_handler_on_paths_differing_in_parameter_names_is_documented_once() -> None:
    @get(["/pairs/{y:int}", "/pairs/{x:int}"])
    async def handler(x: FromPath[int] = 0, y: FromPath[int] = 0) -> None:
        return None

    paths = build_document(handler)["paths"]

    assert list(paths) == ["/pairs/{x}"]
    assert [p["name"] for p in paths["/pairs/{x}"]["get"]["parameters"]] == ["x"]


def test_same_method_on_same_path_format_is_reported_at_startup() -> None:
    @get("/items/{item_id:int}")
    async def by_int(item_id: FromPath[int]) -> str:
        return "int"

    @get("/items/{item_id:str}")
    async def by_str(item_id: FromPath[str]) -> str:
        return "str"

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        Litestar([by_int, by_str])

    message = str(exc_info.value)
    assert f"Route handlers '{by_int}' and '{by_str}' both serve GET on paths that differ only in their path" in message
    assert "registered as '/items/{item_id:int}' and '/items/{item_id:str}'" in message

    app = Litestar([by_int])
    with pytest.raises(ImproperlyConfiguredException, match="both serve GET"):
        app.register(by_str)

    with create_test_client([by_int, by_str], openapi_config=None) as client:
        assert client.get("/items/1").status_code == 200


def test_undocumented_route_neither_conflicts_nor_names_the_shared_path() -> None:
    @get("/things/{a:int}", include_in_schema=False)
    async def hidden(a: FromPath[int]) -> None:
        return None

    @get("/things/{b:str}")
    async def read_thing(b: FromPath[str]) -> None:
        return None

    @post("/things/{b:int}")
    async def create_thing(b: FromPath[int]) -> None:
        return None

    @delete("/things/{c:int}")
    async def delete_thing(c: FromPath[int]) -> None:
        return None

    paths = build_document(hidden, read_thing, create_thing, delete_thing)["paths"]

    assert list(paths) == ["/things/{b}"]
    assert sorted(paths["/things/{b}"]) == ["delete", "get", "post"]
    assert [p["name"] for p in paths["/things/{b}"]["delete"]["parameters"]] == ["b"]
