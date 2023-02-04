from enum import Enum
from typing import Generic, TypeVar
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from pydantic_openapi_schema.v3_1_0 import ExternalDocumentation
from pydantic_openapi_schema.v3_1_0.example import Example
from pydantic_openapi_schema.v3_1_0.schema import Schema

from starlite import Controller, MediaType, Parameter, Provide, Starlite, get
from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.enums import ParamType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.openapi import schema
from starlite.openapi.constants import KWARG_MODEL_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP
from starlite.openapi.schema import (
    get_schema_for_field_type,
    update_schema_with_signature_field,
)
from starlite.params import ParameterKwarg
from starlite.signature.field import SignatureField
from starlite.testing import create_test_client
from tests import TypedDictPerson


def test_update_schema_with_signature_field() -> None:
    test_str = "abc"
    kwarg_model = ParameterKwarg(
        examples=[Example(value=1)],
        external_docs=ExternalDocumentation(url="https://example.com/docs"),  # type: ignore
        content_encoding="utf-8",
        default=test_str,
        title=test_str,
        description=test_str,
        const=True,
        gt=1,
        ge=1,
        lt=1,
        le=1,
        multiple_of=1,
        min_items=1,
        max_items=1,
        min_length=1,
        max_length=1,
        regex="^[a-z]$",
    )
    signature_field = SignatureField.create(field_type=str, kwarg_model=kwarg_model)
    schema = Schema()
    update_schema_with_signature_field(
        schema=schema,
        signature_field=signature_field,
    )
    assert schema.const == test_str
    for signature_key, schema_key in KWARG_MODEL_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP.items():
        assert getattr(schema, schema_key) == getattr(kwarg_model, signature_key)


def test_dependency_schema_generation() -> None:
    def top_dependency(query_param: int) -> int:
        return query_param

    def mid_level_dependency(header_param: str = Parameter(header="header_param", required=False)) -> int:
        return 5

    def local_dependency(path_param: int, mid_level: int, top_level: int) -> int:
        return path_param + mid_level + top_level

    class MyController(Controller):
        path = "/test"
        dependencies = {"mid_level": Provide(mid_level_dependency)}

        @get(
            path="/{path_param:int}",
            dependencies={
                "summed": Provide(local_dependency),
            },
            media_type=MediaType.TEXT,
        )
        def test_function(self, summed: int, handler_param: int) -> str:
            return str(summed)

    with create_test_client(
        MyController,
        dependencies={"top_level": Provide(top_dependency)},
        openapi_config=DEFAULT_OPENAPI_CONFIG,
    ) as client:
        handler = client.app.openapi_schema.paths["/test/{path_param}"]
        data = {param.name: {"in": param.param_in, "required": param.required} for param in handler.get.parameters}
        assert data == {
            "path_param": {"in": ParamType.PATH, "required": True},
            "header_param": {"in": ParamType.HEADER, "required": False},
            "query_param": {"in": ParamType.QUERY, "required": True},
            "handler_param": {"in": ParamType.QUERY, "required": True},
        }


def test_create_schema_for_generic_type_raises_improper_config() -> None:
    T = TypeVar("T")

    class GenericType(Generic[T]):
        t: T

    @get("/")
    def handler_function(dep: GenericType[int]) -> None:
        ...

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler_function])


def test_get_schema_for_field_type_typeddict(monkeypatch: pytest.MonkeyPatch) -> None:
    return_value_mock = MagicMock()
    convert_typeddict_to_model_mock = MagicMock(return_value=return_value_mock)
    openapi_310_pydantic_schema_mock = MagicMock()
    monkeypatch.setattr(schema, "OpenAPI310PydanticSchema", openapi_310_pydantic_schema_mock)
    monkeypatch.setattr(schema, "convert_typeddict_to_model", convert_typeddict_to_model_mock)

    class M(BaseModel):
        data: TypedDictPerson

    get_schema_for_field_type(SignatureField.from_model_field(M.__fields__["data"]), [])
    convert_typeddict_to_model_mock.assert_called_once_with(TypedDictPerson)
    openapi_310_pydantic_schema_mock.assert_called_once_with(schema_class=return_value_mock)


def test_get_schema_for_field_type_enum() -> None:
    class Opts(str, Enum):
        opt1 = "opt1"
        opt2 = "opt2"

    class M(BaseModel):
        opt: Opts

    schema = get_schema_for_field_type(SignatureField.from_model_field(M.__fields__["opt"]), [])
    assert schema.enum == ["opt1", "opt2"]
