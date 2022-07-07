from typing import Callable, Optional, cast

import pytest
from openapi_schema_pydantic.v3.v3_1_0.open_api import OpenAPI

from starlite import Dependency, ImproperlyConfiguredException, Provide, Starlite, get
from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.openapi.enums import OpenAPIType
from starlite.openapi.parameters import create_parameters
from starlite.signature import SignatureModelFactory
from starlite.utils import find_index
from tests.openapi.utils import PersonController


def test_create_parameters() -> None:
    app = Starlite(route_handlers=[PersonController])
    index = find_index(app.routes, lambda x: x.path_format == "/{service_id}/person")
    route = app.routes[index]
    route_handler = route.route_handler_map["GET"][0]  # type: ignore
    parameters = create_parameters(
        route_handler=route_handler,
        handler_fields=SignatureModelFactory(fn=cast(Callable, route_handler.fn), plugins=[], dependency_names=set())
        .create_signature_model()
        .__fields__,
        path_parameters=route.path_parameters,
        generate_examples=True,
    )
    assert len(parameters) == 9
    page, name, page_size, service_id, from_date, to_date, gender, secret_header, cookie_value = tuple(parameters)
    assert service_id.name == "service_id"
    assert service_id.param_in == "path"
    assert service_id.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert service_id.required
    assert service_id.param_schema.examples  # type: ignore
    assert page.param_in == "query"
    assert page.name == "page"
    assert page.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert page.required
    assert page.param_schema.examples  # type: ignore
    assert page_size.param_in == "query"
    assert page_size.name == "pageSize"
    assert page_size.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert page_size.required
    assert page_size.description == "Page Size Description"
    assert page_size.param_schema.examples[0].value == 1  # type: ignore
    assert name.param_in == "query"
    assert name.name == "name"
    assert len(name.param_schema.oneOf) == 3  # type: ignore
    assert not name.required
    assert name.param_schema.examples  # type: ignore
    assert from_date.param_in == "query"
    assert from_date.name == "from_date"
    assert len(from_date.param_schema.oneOf) == 4  # type: ignore
    assert not from_date.required
    assert from_date.param_schema.examples  # type: ignore
    assert to_date.param_in == "query"
    assert to_date.name == "to_date"
    assert len(to_date.param_schema.oneOf) == 4  # type: ignore
    assert not to_date.required
    assert to_date.param_schema.examples  # type: ignore
    assert gender.param_in == "query"
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
    assert secret_header.param_in == "header"
    assert secret_header.param_schema.type == OpenAPIType.STRING  # type: ignore
    assert secret_header.required
    assert secret_header.param_schema.examples  # type: ignore
    assert cookie_value.param_in == "cookie"
    assert cookie_value.param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert cookie_value.required
    assert cookie_value.param_schema.examples  # type: ignore


def test_deduplication_for_param_where_key_and_type_equal() -> None:
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
