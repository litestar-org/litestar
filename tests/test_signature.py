from functools import lru_cache
from typing import Optional

import pytest
from starlette.status import HTTP_204_NO_CONTENT

from starlite import ImproperlyConfiguredException, get
from starlite.signature import SignatureModelFactory


def test_create_function_signature_model_parameter_parsing() -> None:
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    model = SignatureModelFactory(my_fn.fn, [], set()).model()  # type: ignore[arg-type]
    fields = model.__fields__
    assert fields["a"].type_ == int
    assert fields["a"].required
    assert fields["b"].type_ == str
    assert fields["b"].required
    assert fields["c"].type_ == bytes
    assert fields["c"].allow_none
    assert fields["c"].default is None
    assert fields["d"].type_ == bytes
    assert fields["d"].default == b"123"
    assert fields["e"].type_ == dict
    assert fields["e"].allow_none
    assert fields["e"].default is None


def test_create_signature_validation() -> None:
    @get()
    def my_fn(typed: int, untyped) -> None:  # type: ignore
        pass

    with pytest.raises(ImproperlyConfiguredException):
        SignatureModelFactory(my_fn.fn, [], set()).model()  # type: ignore[arg-type]


def test_create_function_signature_model_ignore_return_annotation() -> None:
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return

    signature_model_type = SignatureModelFactory(health_check.fn, [], set()).model()  # type:ignore[arg-type]
    assert signature_model_type().dict() == {}


def test_create_function_signature_model_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        SignatureModelFactory(lru_cache(maxsize=0)(lambda x: x), [], set()).model().dict()  # type: ignore
