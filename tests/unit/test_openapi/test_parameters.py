from typing import TYPE_CHECKING, List, Optional, Type, cast

import pytest

from litestar import Controller, Litestar, Router, get
from litestar._openapi.parameters import create_parameter_for_handler
from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.examples import ExampleFactory
from litestar._openapi.typescript_converter.schema_parsing import is_schema_value
from litestar._signature import SignatureModel
from litestar.di import Provide
from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec import OpenAPI
from litestar.openapi.spec.enums import OpenAPIType
from litestar.params import Dependency, Parameter
from litestar.utils import find_index

if TYPE_CHECKING:
    from litestar.openapi.spec.parameter import Parameter as OpenAPIParameter


def _create_parameters(app: Litestar, path: str) -> List["OpenAPIParameter"]:
    index = find_index(app.routes, lambda x: x.path_format == path)
    route = app.routes[index]
    route_handler = route.route_handler_map["GET"][0]  # type: ignore

    handler = route_handler.fn.value
    assert callable(handler)

    handler_fields = SignatureModel.create(
        dependency_name_set=set(),
        fn=handler,
        data_dto=None,
        parsed_signature=route_handler.parsed_fn_signature,
        type_decoders=[],
    )._fields

    return create_parameter_for_handler(
        route_handler, handler_fields, route.path_parameters, SchemaCreator(generate_examples=True)
    )


def test_create_parameters(person_controller: Type[Controller]) -> None:
    ExampleFactory.seed_random(10)

    parameters = _create_parameters(app=Litestar(route_handlers=[person_controller]), path="/{service_id}/person")
    assert len(parameters) == 9
    page, name, page_size, service_id, from_date, to_date, gender, secret_header, cookie_value = tuple(parameters)

    assert service_id.name == "service_id"
    assert service_id.param_in == ParamType.PATH
    assert is_schema_value(service_id.schema)
    assert service_id.schema.type == OpenAPIType.INTEGER
    assert service_id.required
    assert service_id.schema.examples

    assert page.param_in == ParamType.QUERY
    assert page.name == "page"
    assert is_schema_value(page.schema)
    assert page.schema.type == OpenAPIType.INTEGER
    assert page.required
    assert page.schema.examples

    assert page_size.param_in == ParamType.QUERY
    assert page_size.name == "pageSize"
    assert is_schema_value(page_size.schema)
    assert page_size.schema.type == OpenAPIType.INTEGER
    assert page_size.required
    assert page_size.description == "Page Size Description"
    assert page_size.schema.examples
    assert page_size.schema.examples[0].value == 1

    assert name.param_in == ParamType.QUERY
    assert name.name == "name"
    assert is_schema_value(name.schema)
    assert name.schema.one_of
    assert len(name.schema.one_of) == 3
    assert not name.required
    assert name.schema.examples

    assert from_date.param_in == ParamType.QUERY
    assert from_date.name == "from_date"
    assert is_schema_value(from_date.schema)
    assert from_date.schema.one_of
    assert len(from_date.schema.one_of) == 4
    assert not from_date.required
    assert from_date.schema.examples

    assert to_date.param_in == ParamType.QUERY
    assert to_date.name == "to_date"
    assert is_schema_value(to_date.schema)
    assert to_date.schema.one_of
    assert len(to_date.schema.one_of) == 4
    assert not to_date.required
    assert to_date.schema.examples

    assert gender.param_in == ParamType.QUERY
    assert gender.name == "gender"
    assert is_schema_value(gender.schema)
    assert gender.schema.to_schema() == {
        "oneOf": [
            {"type": "null"},
            {
                "items": {
                    "type": "string",
                    "enum": ["M", "F", "O", "A"],
                    "examples": [{"description": "Example  value", "value": "F"}],
                },
                "type": "array",
                "examples": [{"description": "Example  value", "value": ["A"]}],
            },
            {
                "type": "string",
                "enum": ["M", "F", "O", "A"],
                "examples": [{"description": "Example  value", "value": "M"}],
            },
        ],
        "examples": [{"value": "M"}, {"value": ["M", "O"]}],
    }
    assert not gender.required

    assert secret_header.param_in == ParamType.HEADER
    assert is_schema_value(secret_header.schema)
    assert secret_header.schema.type == OpenAPIType.STRING
    assert secret_header.required
    assert secret_header.schema.examples

    assert cookie_value.param_in == ParamType.COOKIE
    assert is_schema_value(cookie_value.schema)
    assert cookie_value.schema.type == OpenAPIType.INTEGER
    assert cookie_value.required
    assert cookie_value.schema.examples


def test_deduplication_for_param_where_key_and_type_are_equal() -> None:
    class BaseDep:
        def __init__(self, query_param: str) -> None:
            ...

    class ADep(BaseDep):
        ...

    class BDep(BaseDep):
        ...

    async def c_dep(other_param: float) -> float:
        return other_param

    async def d_dep(other_param: float) -> float:
        return other_param

    @get(
        "/test",
        dependencies={
            "a": Provide(ADep, sync_to_thread=False),
            "b": Provide(BDep, sync_to_thread=False),
            "c": Provide(c_dep),
            "d": Provide(d_dep),
        },
    )
    def handler(a: ADep, b: BDep, c: float, d: float) -> str:
        return "OK"

    app = Litestar(route_handlers=[handler])
    assert isinstance(app.openapi_schema, OpenAPI)
    open_api_path_item = app.openapi_schema.paths["/test"]  # type: ignore
    open_api_parameters = open_api_path_item.get.parameters  # type: ignore
    assert len(open_api_parameters) == 2  # type: ignore
    assert {p.name for p in open_api_parameters} == {"query_param", "other_param"}  # type: ignore


def test_raise_for_multiple_parameters_of_same_name_and_differing_types() -> None:
    async def a_dep(query_param: int) -> int:
        return query_param

    async def b_dep(query_param: str) -> int:
        return 1

    @get("/test", dependencies={"a": Provide(a_dep), "b": Provide(b_dep)})
    def handler(a: int, b: int) -> str:
        return "OK"

    app = Litestar(route_handlers=[handler])

    with pytest.raises(ImproperlyConfiguredException):
        app.openapi_schema


def test_dependency_params_in_docs_if_dependency_provided() -> None:
    async def produce_dep(param: str) -> int:
        return 13

    @get(dependencies={"dep": Provide(produce_dep)})
    def handler(dep: Optional[int] = Dependency()) -> None:
        return None

    app = Litestar(route_handlers=[handler])
    param_name_set = {p.name for p in cast("OpenAPI", app.openapi_schema).paths["/"].get.parameters}  # type: ignore
    assert "dep" not in param_name_set
    assert "param" in param_name_set


def test_dependency_not_in_doc_params_if_not_provided() -> None:
    @get()
    def handler(dep: Optional[int] = Dependency()) -> None:
        return None

    app = Litestar(route_handlers=[handler])
    assert cast("OpenAPI", app.openapi_schema).paths["/"].get.parameters is None  # type: ignore


def test_non_dependency_in_doc_params_if_not_provided() -> None:
    @get()
    def handler(param: Optional[int]) -> None:
        return None

    app = Litestar(route_handlers=[handler])
    param_name_set = {p.name for p in cast("OpenAPI", app.openapi_schema).paths["/"].get.parameters}  # type: ignore
    assert "param" in param_name_set


def test_layered_parameters() -> None:
    class MyController(Controller):
        path = "/controller"
        parameters = {
            "controller1": Parameter(lt=100),
            "controller2": Parameter(str, query="controller3"),
        }

        @get("/{local:int}")
        def my_handler(
            self,
            local: int,
            controller1: int,
            router1: str,
            router2: float,
            app1: str,
            app2: List[str],
            controller2: float = Parameter(float, ge=5.0),
        ) -> dict:
            return {}

    router = Router(
        path="/router",
        route_handlers=[MyController],
        parameters={
            "router1": Parameter(str, pattern="^[a-zA-Z]$"),
            "router2": Parameter(float, multiple_of=5.0, header="router3"),
        },
    )

    parameters = _create_parameters(
        app=Litestar(
            route_handlers=[router],
            parameters={
                "app1": Parameter(str, cookie="app4"),
                "app2": Parameter(List[str], min_items=2),
                "app3": Parameter(bool, required=False),
            },
        ),
        path="/router/controller/{local}",
    )
    local, app3, controller1, router1, router3, app4, app2, controller3 = tuple(parameters)

    assert app4.param_in == ParamType.COOKIE
    assert app4.schema.type == OpenAPIType.STRING  # type: ignore
    assert app4.required
    assert app4.schema.examples  # type: ignore

    assert app2.param_in == ParamType.QUERY
    assert app2.schema.type == OpenAPIType.ARRAY  # type: ignore
    assert app2.required
    assert app2.schema.examples  # type: ignore

    assert app3.param_in == ParamType.QUERY
    assert app3.schema.type == OpenAPIType.BOOLEAN  # type: ignore
    assert not app3.required
    assert app3.schema.examples  # type: ignore

    assert router1.param_in == ParamType.QUERY
    assert router1.schema.type == OpenAPIType.STRING  # type: ignore
    assert router1.required
    assert router1.schema.pattern == "^[a-zA-Z]$"  # type: ignore
    assert router1.schema.examples  # type: ignore

    assert router3.param_in == ParamType.HEADER
    assert router3.schema.type == OpenAPIType.NUMBER  # type: ignore
    assert router3.required
    assert router3.schema.multipleOf == 5.0  # type: ignore
    assert router3.schema.examples  # type: ignore

    assert controller1.param_in == ParamType.QUERY
    assert controller1.schema.type == OpenAPIType.INTEGER  # type: ignore
    assert controller1.required
    assert controller1.schema.exclusiveMaximum == 100.0  # type: ignore
    assert controller1.schema.examples  # type: ignore

    assert controller3.param_in == ParamType.QUERY
    assert controller3.schema.type == OpenAPIType.NUMBER  # type: ignore
    assert controller3.required
    assert controller3.schema.minimum == 5.0  # type: ignore
    assert controller3.schema.examples  # type: ignore

    assert local.param_in == ParamType.PATH
    assert local.schema.type == OpenAPIType.INTEGER  # type: ignore
    assert local.required
    assert local.schema.examples  # type: ignore
