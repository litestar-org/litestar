from typing import Generic, TypeVar, cast

import pytest
from openapi_schema_pydantic import Example
from openapi_schema_pydantic.v3.v3_1_0.schema import Schema
from pydantic.fields import FieldInfo

from starlite import Controller, MediaType, Parameter, Provide, Starlite, get
from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.exceptions import ImproperlyConfiguredException
from starlite.openapi.constants import (
    EXTRA_TO_OPENAPI_PROPERTY_MAP,
    PYDANTIC_TO_OPENAPI_PROPERTY_MAP,
)
from starlite.openapi.schema import update_schema_with_field_info
from starlite.testing import create_test_client


def test_update_schema_with_field_info() -> None:
    test_str = "abc"
    extra = {
        "examples": [Example(value=1)],
        "external_docs": "https://example.com/docs",
        "content_encoding": "utf-8",
    }
    field_info = FieldInfo(
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
        **extra,
    )
    schema = Schema()
    update_schema_with_field_info(schema=schema, field_info=field_info)
    assert schema.const == field_info.default
    for pydantic_key, schema_key in PYDANTIC_TO_OPENAPI_PROPERTY_MAP.items():
        assert getattr(schema, schema_key) == getattr(field_info, pydantic_key)
    for extra_key, schema_key in EXTRA_TO_OPENAPI_PROPERTY_MAP.items():
        assert getattr(schema, schema_key) == field_info.extra[extra_key]


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
        app = cast(Starlite, client.app)
        handler = app.openapi_schema.paths["/test/{path_param}"]
        data = {param.name: {"in": param.param_in, "required": param.required} for param in handler.get.parameters}
        assert data == {
            "path_param": {"in": "path", "required": True},
            "header_param": {"in": "header", "required": False},
            "query_param": {"in": "query", "required": True},
            "handler_param": {"in": "query", "required": True},
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
