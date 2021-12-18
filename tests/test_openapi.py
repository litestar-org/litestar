from datetime import date, datetime
from enum import Enum
from inspect import Signature
from typing import Any, Callable, List, Optional, Union, cast

import yaml
from hypothesis import given
from hypothesis import strategies as st
from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from pydantic.types import (
    conbytes,
    condecimal,
    confloat,
    conint,
    conlist,
    conset,
    constr,
)
from starlette.responses import HTMLResponse
from starlette.status import HTTP_200_OK

from starlite import (
    Controller,
    Header,
    MediaType,
    Partial,
    Router,
    Starlite,
    create_test_client,
    delete,
    get,
    patch,
    post,
    put,
)
from starlite.enums import OpenAPIMediaType
from starlite.openapi import (
    OpenAPIConfig,
    OpenAPIType,
    create_collection_constrained_field_schema,
    create_constrained_field_schema,
    create_numerical_constrained_field_schema,
    create_parameters,
    create_parsed_model_field,
    create_path_item,
    create_path_parameter,
    create_request_body,
    create_responses,
    create_string_constrained_field_schema,
    get_media_type,
)
from starlite.request import create_function_signature_model
from starlite.utils import find_index
from tests.utils import Person, Pet, ResponseHeaders, VanillaDataClassPerson


class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    ANY = "A"


class PersonController(Controller):
    path = "/{service_id:int}/person"

    @get()
    def get_persons(
        self,
        # expected to be ignored
        headers: Any,
        request: Any,
        # required query parameters below
        page: int,
        page_size: int,
        name: Optional[Union[str, List[str]]],  # intentionally without default
        # path parameter
        service_id: int = conint(gt=0),
        # non-required query parameters below
        from_date: Optional[Union[int, datetime, date]] = None,
        to_date: Optional[Union[int, datetime, date]] = None,
        gender: Optional[Union[Gender, List[Gender]]] = None,
        # header parameter
        secret_header: str = Header("secret"),
    ) -> List[Person]:
        pass

    @post()
    def create_person(self, data: Person, secret_header: str = Header("secret"), media_type=MediaType.TEXT) -> Person:
        pass

    @post(path="/bulk")
    def bulk_create_person(self, data: List[Person], secret_header: str = Header("secret")) -> List[Person]:
        pass

    @put(path="/bulk")
    def bulk_update_person(self, data: List[Person], secret_header: str = Header("secret")) -> List[Person]:
        pass

    @patch(path="/bulk")
    def bulk_partial_update_person(
        self, data: List[Partial[Person]], secret_header: str = Header("secret")
    ) -> List[Person]:
        pass

    @get(path="/{person_id:str}")
    def get_person_by_id(self, person_id: str) -> Person:
        pass

    @patch(path="/{person_id:str}")
    def partial_update_person(self, person_id: str, data: Partial[Person]) -> Person:
        pass

    @put(path="/{person_id:str}")
    def update_person(self, person_id: str, data: Person) -> Person:
        pass

    @delete(path="/{person_id:str}", response_class=HTMLResponse)
    def delete_person(self, person_id: str) -> None:
        pass

    @get(path="/dataclass")
    def get_person_dataclass(self) -> VanillaDataClassPerson:
        pass


class PetController(Controller):
    path = "/pet"

    @get()
    def pets(self) -> List[Pet]:
        pass

    @get(path="/owner-or-pet", response_headers=ResponseHeaders(x_my_tag="123"))
    def get_pets_or_owners(self) -> List[Union[Person, Pet]]:
        pass


constrained_numbers = [
    conint(gt=10, lt=100),
    conint(ge=10, le=100),
    conint(ge=10, le=100, multiple_of=7),
    confloat(gt=10, lt=100),
    confloat(ge=10, le=100),
    confloat(ge=10, le=100, multiple_of=4.2),
    confloat(gt=10, lt=100, multiple_of=10),
    condecimal(gt=10, lt=100),
    condecimal(ge=10, le=100),
    condecimal(gt=10, lt=100, multiple_of=5),
    condecimal(ge=10, le=100, multiple_of=2),
]

constrained_string = [
    constr(regex="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=1, regex="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=10, regex="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=10, max_length=100, regex="^[a-zA-Z]$"),
    constr(min_length=1),
    constr(min_length=10),
    constr(min_length=10, max_length=100),
    conbytes(to_lower=True, min_length=1),
    conbytes(to_lower=True, min_length=10),
    conbytes(to_lower=True, min_length=10, max_length=100),
    conbytes(min_length=1),
    conbytes(min_length=10),
    conbytes(min_length=10, max_length=100),
]

constrained_collection = [
    conlist(int, min_items=1),
    conlist(int, min_items=1, max_items=10),
    conset(int, min_items=1),
    conset(int, min_items=1, max_items=10),
]


def test_openapi_yaml():
    with create_test_client([PersonController, PetController], openapi_config=OpenAPIConfig()) as client:
        app = cast(Starlite, client.app)
        assert app.router.openapi_schema
        openapi_schema = app.router.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_YAML.value
        assert yaml.safe_load(response.content) == construct_open_api_with_schema_class(app.router.openapi_schema).dict(
            exclude_none=True
        )


def test_openapi_json():
    with create_test_client(
        [PersonController, PetController],
        openapi_config=OpenAPIConfig(schema_response_media_type=OpenAPIMediaType.OPENAPI_JSON),
    ) as client:
        app = cast(Starlite, client.app)
        assert app.router.openapi_schema
        openapi_schema = app.router.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_JSON.value
        assert response.json() == construct_open_api_with_schema_class(app.router.openapi_schema).dict(
            exclude_none=True
        )


@given(
    field_type=st.sampled_from(constrained_collection),
)
def test_create_collection_constrained_field_schema(field_type):
    schema = create_collection_constrained_field_schema(field_type=field_type, sub_fields=None)
    assert schema.type == OpenAPIType.ARRAY
    assert schema.items.type == OpenAPIType.INTEGER
    assert schema.minItems == field_type.min_items
    assert schema.maxItems == field_type.max_items


def test_create_collection_constrained_field_schema_sub_fields():
    field_type = List[Union[str, int]]
    for pydantic_fn in [conlist, conset]:
        schema = create_collection_constrained_field_schema(
            field_type=pydantic_fn(field_type, min_items=1, max_items=10),
            sub_fields=create_parsed_model_field(field_type).sub_fields,
        )
        assert schema.type == OpenAPIType.ARRAY
        expected = {
            "items": [{"oneOf": [{"type": "string"}, {"type": "integer"}]}],
            "type": "array",
            "maxItems": 10,
            "minItems": 1,
        }
        if pydantic_fn == conset:
            # set should have uniqueItems always
            expected["uniqueItems"] = True

        assert schema.dict(exclude_none=True) == expected


@given(field_type=st.sampled_from(constrained_string))
def test_create_string_constrained_field_schema(field_type):
    schema = create_string_constrained_field_schema(field_type=field_type)
    assert schema.type == OpenAPIType.STRING
    assert schema.minLength == field_type.min_length
    assert schema.maxLength == field_type.max_length
    if hasattr(field_type, "regex"):
        assert schema.pattern == field_type.regex
    if field_type.to_lower:
        assert schema.description


@given(field_type=st.sampled_from(constrained_numbers))
def test_create_numerical_constrained_field_schema(field_type):
    schema = create_numerical_constrained_field_schema(field_type=field_type)
    assert schema.type == OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER
    assert schema.exclusiveMinimum == field_type.gt
    assert schema.minimum == field_type.ge
    assert schema.exclusiveMaximum == field_type.lt
    assert schema.maximum == field_type.le
    assert schema.exclusiveMinimum == field_type.gt
    assert schema.multipleOf == field_type.multiple_of


@given(field_type=st.sampled_from([*constrained_numbers, *constrained_collection, *constrained_string]))
def test_create_constrained_field_schema(field_type):
    schema = create_constrained_field_schema(field_type=field_type, sub_fields=None)
    assert schema


def test_create_path_parameter():
    app = Starlite(route_handlers=[PersonController])
    index = find_index(app.router.routes, lambda x: x.path_format == "/{service_id}/person")
    route = app.router.routes[index]
    service_id = create_path_parameter(route.path_parameters[0])
    assert service_id.name == "service_id"
    assert service_id.param_in == "path"
    assert service_id.param_schema.type == OpenAPIType.INTEGER
    assert service_id.required


def test_create_parameters():
    app = Starlite(route_handlers=[PersonController])
    index = find_index(app.router.routes, lambda x: x.path_format == "/{service_id}/person")
    route = app.router.routes[index]
    route_handler = PersonController.get_persons
    parameters = create_parameters(
        route_handler=route_handler,
        handler_fields=create_function_signature_model(fn=cast(Callable, route_handler.fn)).__fields__,
        path_parameters=route.path_parameters,
    )
    assert len(parameters) == 7
    page, page_size, name, from_date, to_date, gender, secret_header = tuple(parameters)
    assert page.param_in == "query"
    assert page.name == "page"
    assert page.param_schema.type == OpenAPIType.INTEGER
    assert page.required
    assert page_size.param_in == "query"
    assert page_size.name == "page_size"
    assert page_size.param_schema.type == OpenAPIType.INTEGER
    assert page_size.required
    assert name.param_in == "query"
    assert name.name == "name"
    assert name.param_schema.dict(exclude_none=True) == {
        "oneOf": [{"type": "string"}, {"items": [{"type": "string"}], "type": "array"}]
    }
    assert name.required
    assert from_date.param_in == "query"
    assert from_date.name == "from_date"
    assert from_date.param_schema.dict(exclude_none=True) == {
        "oneOf": [
            {"type": "null"},
            {
                "oneOf": [
                    {"type": "integer"},
                    {"type": "string", "schema_format": "date-time"},
                    {"type": "string", "schema_format": "date"},
                ]
            },
        ]
    }
    assert not from_date.required
    assert to_date.param_in == "query"
    assert to_date.name == "to_date"
    assert to_date.param_schema.dict(exclude_none=True) == {
        "oneOf": [
            {"type": "null"},
            {
                "oneOf": [
                    {"type": "integer"},
                    {"type": "string", "schema_format": "date-time"},
                    {"type": "string", "schema_format": "date"},
                ]
            },
        ]
    }
    assert not to_date.required
    assert gender.param_in == "query"
    assert gender.name == "gender"
    assert gender.param_schema.dict(exclude_none=True) == {
        "oneOf": [
            {"type": "null"},
            {
                "oneOf": [
                    {"type": "string", "enum": ["M", "F", "O", "A"]},
                    {"items": [{"type": "string", "enum": ["M", "F", "O", "A"]}], "type": "array"},
                ]
            },
        ]
    }
    assert not gender.required
    assert secret_header.param_in == "header"
    assert secret_header.param_schema.type == OpenAPIType.STRING
    assert secret_header.required


def test_create_path_item():
    router = Router(path="", route_handlers=[PersonController])
    index = find_index(router.routes, lambda x: x.path_format == "/{service_id}/person/{person_id}")
    route = router.routes[index]
    schema = create_path_item(route=route)
    assert schema.delete
    assert schema.delete.operationId == "delete_person"
    assert schema.get
    assert schema.get.operationId == "get_person_by_id"
    assert schema.patch
    assert schema.patch.operationId == "partial_update_person"
    assert schema.put
    assert schema.put.operationId == "update_person"


def test_create_responses():
    for route in Starlite(route_handlers=[PersonController]).router.routes:
        for route_handler in route.route_handler_map.values():
            responses = create_responses(route_handler=route_handler)
            if Signature.from_callable(cast(Callable, route_handler.fn)).return_annotation:
                assert responses
            else:
                assert not responses

    responses = create_responses(PetController.get_pets_or_owners)
    assert "200" in responses
    response = responses["200"]
    assert response.headers["application-type"].param_schema.type == OpenAPIType.STRING
    assert response.headers["Access-Control-Allow-Origin"].param_schema.type == OpenAPIType.STRING
    assert response.headers["x-my-tag"].param_schema.type == OpenAPIType.STRING
    assert len(response.headers["omitted-tag"].param_schema.oneOf) == 2


def test_get_media_type():
    for route in Starlite(route_handlers=[PersonController]).router.routes:
        for route_handler in route.route_handler_map.values():
            media_type = get_media_type(route_handler=route_handler)
            if route_handler.media_type:
                assert media_type == route_handler.media_type
            elif route_handler.response_class:
                assert media_type == route_handler.response_class.media_type
            else:
                assert media_type == MediaType.JSON


def test_create_request_body():
    for route in Starlite(route_handlers=[PersonController]).router.routes:
        for route_handler in route.route_handler_map.values():
            handler_fields = route_handler.__fields__
            request_body = create_request_body(route_handler=route_handler, handler_fields=handler_fields)
            if "data" in handler_fields:
                assert request_body
            else:
                assert not request_body
