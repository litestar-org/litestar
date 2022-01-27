from typing import Optional

import pytest

from starlite import ImproperlyConfiguredException, get
from starlite.utils import model_function_signature


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
