from typing import Generic, TypeVar

import pytest

from starlite.openapi.schema import create_schema
from starlite.signature import model_function_signature


@pytest.mark.xfail  # type:ignore[misc]
def test_create_schema_generic_type_field() -> None:
    T = TypeVar("T")

    class GenericType(Generic[T]):
        t: T

    def handler_function(dep: GenericType[int]) -> None:
        ...

    model = model_function_signature(handler_function, plugins=[])
    create_schema(model.__fields__["dep"], generate_examples=False)
