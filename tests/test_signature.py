from functools import lru_cache
from typing import Optional

import pytest
from starlette.status import HTTP_204_NO_CONTENT

from starlite import ImproperlyConfiguredException, Provide, get
from starlite.params import Dependency
from starlite.signature import SignatureModelFactory
from starlite.testing import create_test_client


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


def test_dependency_validation_failure_raises_500() -> None:

    dependencies = {"dep": Provide(lambda: "thirteen")}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(route_handlers=[test], dependencies=dependencies) as client:
        resp = client.get("/?param=13")

    assert resp.json() == {
        "detail": "A dependency failed validation for GET http://testserver/?param=13",
        "extra": [{"loc": ["dep"], "msg": "value is not a valid integer", "type": "type_error.integer"}],
        "status_code": 500,
    }


def test_validation_failure_raises_400() -> None:

    dependencies = {"dep": Provide(lambda: 13)}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(route_handlers=[test], dependencies=dependencies) as client:
        resp = client.get("/?param=thirteen")

    assert resp.json() == {
        "detail": "Validation failed for GET http://testserver/?param=thirteen",
        "extra": [{"loc": ["param"], "msg": "value is not a valid integer", "type": "type_error.integer"}],
        "status_code": 400,
    }


def test_client_error_precedence_over_server_error() -> None:

    dependencies = {"dep": Provide(lambda: "thirteen"), "optional_dep": Provide(lambda: "thirty-one")}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(route_handlers=[test], dependencies=dependencies) as client:
        resp = client.get("/?param=thirteen")

    assert resp.json() == {
        "detail": "Validation failed for GET http://testserver/?param=thirteen",
        "extra": [{"loc": ["param"], "msg": "value is not a valid integer", "type": "type_error.integer"}],
        "status_code": 400,
    }
