from typing import Dict, Generic

import pytest
from pydantic import BaseModel
from typing_extensions import Any, TypeVar

from litestar.contrib.pydantic.utils import pydantic_get_type_hints_with_generics_resolved

T = TypeVar("T")


class GenericPydanticModel(BaseModel, Generic[T]):
    foo: T


@pytest.mark.parametrize(
    ("annotation", "expected_type_hints"),
    (
        (GenericPydanticModel, {"foo": T}),
        (GenericPydanticModel[int], {"foo": int}),
    ),
)
def test_get_pydantic_type_hints_with_generics_resolved(annotation: Any, expected_type_hints: Dict[str, Any]) -> None:
    assert pydantic_get_type_hints_with_generics_resolved(annotation) == expected_type_hints
