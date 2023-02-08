from enum import Enum
from typing import Any, AnyStr

import pytest
from pydantic.types import PaymentCardBrand

from starlite import MediaType, get
from tests import Person


class MyEnum(Enum):
    first = 1


class MyBytes(bytes):
    ...


@pytest.mark.parametrize(
    "annotation, expected_media_type",
    (
        (str, MediaType.TEXT),
        (bytes, MediaType.TEXT),
        (AnyStr, MediaType.TEXT),
        (MyBytes, MediaType.TEXT),
        (PaymentCardBrand, MediaType.TEXT),
        (MyEnum, MediaType.JSON),
        (dict, MediaType.JSON),
        (Person, MediaType.JSON),
    ),
)
def test_media_type_inference(annotation: Any, expected_media_type: MediaType) -> None:
    @get("/")
    def handler() -> annotation:
        return None

    assert handler.media_type == expected_media_type
