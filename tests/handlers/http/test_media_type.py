from enum import Enum
from pathlib import Path
from typing import Any, AnyStr

import pytest
from pydantic import ByteSize, ConstrainedFloat
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
        (int, MediaType.TEXT),
        (float, MediaType.TEXT),
        (AnyStr, MediaType.TEXT),
        (MyBytes, MediaType.TEXT),
        (PaymentCardBrand, MediaType.TEXT),
        (ByteSize, MediaType.TEXT),
        (ConstrainedFloat, MediaType.TEXT),
        (MyEnum, MediaType.TEXT),
        (Path, MediaType.TEXT),
        (dict, MediaType.JSON),
        (Person, MediaType.JSON),
    ),
)
def test_media_type_inference(annotation: Any, expected_media_type: MediaType) -> None:
    @get("/")
    def handler() -> annotation:  # type: ignore
        return None

    assert handler.media_type == expected_media_type
