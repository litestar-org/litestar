from typing import Callable, List, Optional, cast

import pytest
from openapi_schema_pydantic.v3.v3_1_0.open_api import OpenAPI
from openapi_schema_pydantic.v3.v3_1_0.parameter import (  # noqa: TC002
    Parameter as OpenAPIParameter,
)

from starlite import Controller, Dependency, ImproperlyConfiguredException
from starlite import Parameter as StarliteParameter
from starlite import Provide, Router, Starlite, get
from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.enums import ParamType
from starlite.openapi.enums import OpenAPIType
from starlite.openapi.parameters import create_parameter_for_handler
from starlite.signature import SignatureModelFactory
from starlite.utils import find_index
from tests.openapi.utils import PersonController


def _create_parameters(app: Starlite, path: str) -> List[OpenAPIParameter]:
    index = find_index(app.routes, lambda x: x.path_format == path)
    route = app.routes[index]
    route_handler = route.route_handler_map["GET"][0]  # type: ignore
    handler_fields = (
        SignatureModelFactory(fn=cast(Callable, route_handler.fn), plugins=[], dependency_names=set())
        .create_signature_model()
        .__fields__
    )
    return create_parameter_for_handler(
        route_handler=route_handler,
        handler_fields=handler_fields,
        path_parameters=route.path_parameters,
        generate_examples=True,
    )


def test_create_parameters() -> None:
    parameters = _create_parameters(app=Starlite(route_handlers=[PersonController]), path="/{service_id}/person")
    assert len(parameters) == 9
    page, name, page_size, service_id, from_date, to_date, gender, secret_header, cookie_value = tuple(parameters)

    assert service_id.name == "service_id"
    assert service_id.param_in == ParamType.PATH
    assert service_id.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert service_id.required
    assert service_id.param_schema.examples  # type: ignore

    assert page.param_in == ParamType.QUERY
    assert page.name == "page"
    assert page.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert page.required
    assert page.param_schema.examples  # type: ignore

    assert page_size.param_in == ParamType.QUERY
    assert page_size.name == "pageSize"
    assert page_size.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert page_size.required
    assert page_size.description == "Page Size Description"
    assert page_size.param_schema.examples[0].value == 1  # type: ignore

    assert name.param_in == ParamType.QUERY
    assert name.name == "name"
    assert len(name.param_schema.oneOf) == 3  # type: ignore
    assert not name.required
    assert name.param_schema.examples  # type: ignore

    assert from_date.param_in == ParamType.QUERY
    assert from_date.name == "from_date"
    assert len(from_date.param_schema.oneOf) == 4  # type: ignore
    assert not from_date.required
    assert from_date.param_schema.examples  # type: ignore

    assert to_date.param_in == ParamType.QUERY
    assert to_date.name == "to_date"
    assert len(to_date.param_schema.oneOf) == 4  # type: ignore
    assert not to_date.required
    assert to_date.param_schema.examples  # type: ignore

    assert gender.param_in == ParamType.QUERY
    assert gender.name == "gender"
    assert gender.param_schema.dict(exclude_none=True) == {  # type: ignore
        "oneOf": [
            {"type": "null"},
            {"type": "string", "enum": ["M", "F", "O", "A"]},
            {"items": {"type": "string", "enum": ["M", "F", "O", "A"]}, "type": "array"},
        ],
        "examples": [{"value": "M"}, {"value": ["M", "O"]}],
    }
    assert not gender.required

    assert secret_header.param_in == ParamType.HEADER
    assert secret_header.param_schema.type == OpenAPIType.STRING  # type: ignore
    assert secret_header.required
    assert secret_header.param_schema.examples  # type: ignore

    assert cookie_value.param_in == ParamType.COOKIE
    assert cookie_value.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert cookie_value.required
    assert cookie_value.param_schema.examples  # type: ignore


def test_deduplication_for_param_where_key_and_type_are_equal() -> None:
    class BaseDep:
        def __init__(self, query_param: str) -> None:
            ...

    class ADep(BaseDep):
        ...

    class BDep(BaseDep):
        ...

    def c_dep(other_param: float) -> float:
        ...

    def d_dep(other_param: float) -> float:
        ...

    @get("/test", dependencies={"a": Provide(ADep), "b": Provide(BDep), "c": Provide(c_dep), "d": Provide(d_dep)})
    def handler(a: ADep, b: BDep, c: float, d: float) -> str:
        return "OK"

    app = Starlite(route_handlers=[handler], openapi_config=DEFAULT_OPENAPI_CONFIG)
    open_api_path_item = cast(OpenAPI, app.openapi_schema).paths["/test"]  # type: ignore
    open_api_parameters = open_api_path_item.get.parameters  # type: ignore
    assert len(open_api_parameters) == 2  # type: ignore
    assert {p.name for p in open_api_parameters} == {"query_param", "other_param"}  # type: ignore


def test_raise_for_multiple_parameters_of_same_name_and_differing_types() -> None:
    def a_dep(query_param: int) -> int:
        ...

    def b_dep(query_param: str) -> int:
        ...

    @get("/test", dependencies={"a": Provide(a_dep), "b": Provide(b_dep)})
    def handler(a: int, b: int) -> str:
        return "OK"

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler], openapi_config=DEFAULT_OPENAPI_CONFIG)


def test_dependency_params_in_docs_if_dependency_provided() -> None:
    def produce_dep(param: str) -> int:
        return 13

    @get(dependencies={"dep": Provide(produce_dep)})
    def handler(dep: Optional[int] = Dependency()) -> None:
        ...

    app = Starlite(route_handlers=[handler])
    param_name_set = {p.name for p in cast(OpenAPI, app.openapi_schema).paths["/"].get.parameters}  # type: ignore
    assert "dep" not in param_name_set
    assert "param" in param_name_set


def test_dependency_not_in_doc_params_if_not_provided() -> None:
    @get()
    def handler(dep: Optional[int] = Dependency()) -> None:
        ...

    app = Starlite(route_handlers=[handler])
    assert cast(OpenAPI, app.openapi_schema).paths["/"].get.parameters is None  # type: ignore


def test_non_dependency_in_doc_params_if_not_provided() -> None:
    @get()
    def handler(param: Optional[int]) -> None:
        ...

    app = Starlite(route_handlers=[handler])
    param_name_set = {p.name for p in cast(OpenAPI, app.openapi_schema).paths["/"].get.parameters}  # type: ignore
    assert "param" in param_name_set


def test_layered_parameters() -> None:
    class MyController(Controller):
        path = "/controller"
        parameters = {
            "controller1": StarliteParameter(lt=100),
            "controller2": StarliteParameter(str, query="controller3"),
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
            controller2: float = StarliteParameter(ge=5.0),
        ) -> dict:
            ...

    router = Router(
        path="/router",
        route_handlers=[MyController],
        parameters={
            "router1": StarliteParameter(str, regex="^[a-zA-Z]$"),
            "router2": StarliteParameter(float, multiple_of=5.0, header="router3"),
        },
    )

    parameters = _create_parameters(
        app=Starlite(
            route_handlers=[router],
            parameters={
                "app1": StarliteParameter(str, cookie="app4"),
                "app2": StarliteParameter(List[str], min_items=2),
                "app3": StarliteParameter(bool, required=False),
            },
        ),
        path="/router/controller/{local}",
    )
    local, app3, controller1, router1, router3, app4, app2, controller3 = tuple(parameters)

    assert app4.param_in == ParamType.COOKIE
    assert app4.param_schema.type == OpenAPIType.STRING  # type: ignore
    assert app4.required
    assert app4.param_schema.examples  # type: ignore

    assert app2.param_in == ParamType.QUERY
    assert app2.param_schema.type == OpenAPIType.ARRAY  # type: ignore
    assert app2.required
    assert app2.param_schema.examples  # type: ignore

    assert app3.param_in == ParamType.QUERY
    assert app3.param_schema.type == OpenAPIType.BOOLEAN  # type: ignore
    assert not app3.required
    assert app3.param_schema.examples  # type: ignore

    assert router1.param_in == ParamType.QUERY
    assert router1.param_schema.type == OpenAPIType.STRING  # type: ignore
    assert router1.required
    assert router1.param_schema.pattern == "^[a-zA-Z]$"  # type: ignore
    assert router1.param_schema.examples  # type: ignore

    assert router3.param_in == ParamType.HEADER
    assert router3.param_schema.type == OpenAPIType.NUMBER  # type: ignore
    assert router3.required
    assert router3.param_schema.multipleOf == 5.0  # type: ignore
    assert router3.param_schema.examples  # type: ignore

    assert controller1.param_in == ParamType.QUERY
    assert controller1.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert controller1.required
    assert controller1.param_schema.exclusiveMaximum == 100.0  # type: ignore
    assert controller1.param_schema.examples  # type: ignore

    assert controller3.param_in == ParamType.QUERY
    assert controller3.param_schema.type == OpenAPIType.NUMBER  # type: ignore
    assert controller3.required
    assert controller3.param_schema.minimum == 5.0  # type: ignore
    assert controller3.param_schema.examples  # type: ignore

    assert local.param_in == ParamType.PATH
    assert local.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert local.required
    assert local.param_schema.examples  # type: ignore
