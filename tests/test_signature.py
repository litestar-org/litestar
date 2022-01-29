from functools import lru_cache
from typing import Optional

import pytest
from starlette.status import HTTP_204_NO_CONTENT

from starlite import ImproperlyConfiguredException, get
from starlite.signature import model_function_signature


def test_create_function_signature_model_parameter_parsing():
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    model = model_function_signature(my_fn.fn, [])
    fields = model.__fields__
    assert fields.get("a").type_ == int
    assert fields.get("a").required
    assert fields.get("b").type_ == str
    assert fields.get("b").required
    assert fields.get("c").type_ == bytes
    assert fields.get("c").allow_none
    assert fields.get("c").default is None
    assert fields.get("d").type_ == bytes
    assert fields.get("d").default == b"123"
    assert fields.get("e").type_ == dict
    assert fields.get("e").allow_none
    assert fields.get("e").default is None


def test_create_signature_validation():
    @get()
    def my_fn(typed: int, untyped) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        model_function_signature(my_fn.fn, [])


def test_create_function_signature_model_ignore_return_annotation():
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return

    assert model_function_signature(health_check.fn, [])().dict() == {}


def test_create_function_signature_model_validation():
    with pytest.raises(ImproperlyConfiguredException):
        model_function_signature(lru_cache(maxsize=0)(lambda x: x), [])
