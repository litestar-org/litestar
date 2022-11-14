from functools import lru_cache
from typing import TYPE_CHECKING, Any, List, Optional, Set, Type, cast
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ValidationError
from pydantic.error_wrappers import ErrorWrapper

from starlite import Provide, get
from starlite.connection import WebSocket
from starlite.datastructures import URL
from starlite.exceptions import (
    ImproperlyConfiguredException,
    InternalServerException,
    ValidationException,
)
from starlite.params import Dependency
from starlite.signature import SignatureModel, SignatureModelFactory
from starlite.status_codes import HTTP_204_NO_CONTENT
from starlite.testing import RequestFactory, TestClient, create_test_client
from tests.plugins.test_base import AModel, APlugin

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Callable

    from pydantic.error_wrappers import ErrorDict

    from starlite import HTTPException
    from starlite.plugins.base import PluginProtocol
    from starlite.types import AnyCallable


def make_signature_model(
    fn: "AnyCallable",
    plugins: Optional[List["PluginProtocol"]] = None,
    provided_dependency_names: Optional[Set[str]] = None,
) -> Type[SignatureModel]:
    return SignatureModelFactory(
        fn=fn, plugins=plugins or [], dependency_names=provided_dependency_names or set()
    ).create_signature_model()


def test_parses_values_from_connection_kwargs_with_plugin() -> None:
    def fn(a: AModel, b: int) -> None:
        pass

    model = make_signature_model(fn, plugins=[APlugin()])
    arbitrary_a = {"name": 1}
    result = model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a=arbitrary_a, b=1)
    assert result == {"a": AModel(name="1"), "b": 1}


def test_parses_values_from_connection_kwargs_without_plugin() -> None:
    class MyModel(BaseModel):
        name: str

    def fn(a: MyModel) -> None:
        pass

    model = make_signature_model(fn)
    result = model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a={"name": "my name"})
    assert result == {"a": MyModel(name="my name")}


def test_parses_values_from_connection_kwargs_raises() -> None:
    def fn(a: int) -> None:
        pass

    model = make_signature_model(fn)
    with pytest.raises(ValidationException):
        model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a="not an int")


def test_resolve_field_value() -> None:
    def fn(a: AModel, b: int) -> None:
        pass

    model: Any = make_signature_model(fn, plugins=[APlugin()])
    instance: SignatureModel = model(a={"name": "my name"}, b=2)
    assert instance.resolve_field_value("a") == AModel(name="my name")
    assert instance.resolve_field_value("b") == 2


@pytest.mark.parametrize(
    ["exc_type", "loc_errors", "extra_loc"],
    [[InternalServerException, ["a"], "a"], [ValidationException, ["a", "b"], "b"]],
)
def test_construct_exception(exc_type: Type[Exception], loc_errors: List[str], extra_loc: str) -> None:
    def fn() -> None:
        pass

    model = make_signature_model(fn, provided_dependency_names={"a"})
    request = RequestFactory().get()
    errors = [ErrorWrapper(Exception(), loc) for loc in loc_errors]
    validation_error = ValidationError(errors=errors, model=BaseModel)
    exc = cast("HTTPException", model.construct_exception(connection=request, exc=validation_error))

    assert isinstance(exc, exc_type)
    assert request.method in exc.detail
    assert str(request.url) in exc.detail
    assert exc.extra == [{"loc": (extra_loc,), "msg": "", "type": "value_error.exception"}]


def test_is_server_error() -> None:
    def fn() -> None:
        pass

    model = make_signature_model(fn, provided_dependency_names={"a"})

    def error_dict(loc: str) -> "ErrorDict":
        return {"loc": (loc,), "msg": "", "type": ""}

    assert model.is_server_error(error_dict("a")) is True
    assert model.is_server_error(error_dict("b")) is False


class TestGetConnectionMethodAndUrl:
    def test_websocket(self) -> None:
        obj = cast("Any", object())
        scope = {"type": "websocket", "path": "/", "headers": []}
        web_socket: WebSocket[Any, Any] = WebSocket(scope=scope, receive=obj, send=obj)  # type: ignore
        assert SignatureModel.get_connection_method_and_url(web_socket) == ("websocket", URL("/"))

    def test_request(self) -> None:
        request = RequestFactory().get()
        assert SignatureModel.get_connection_method_and_url(request) == (request.method, request.url)


def test_create_function_signature_model_parameter_parsing() -> None:
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    model = SignatureModelFactory(my_fn.fn.value, [], set()).create_signature_model()
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
        SignatureModelFactory(my_fn.fn.value, [], set()).create_signature_model()


def test_create_function_signature_model_ignore_return_annotation() -> None:
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return None

    signature_model_type = SignatureModelFactory(health_check.fn.value, [], set()).create_signature_model()
    assert signature_model_type().dict() == {}


def test_create_function_signature_model_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        SignatureModelFactory(lru_cache(maxsize=0)(lambda x: x), [], set()).create_signature_model().dict()  # type: ignore


def test_dependency_validation_failure_raises_500() -> None:
    dependencies = {"dep": Provide(lambda: "thirteen")}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(route_handlers=[test], dependencies=dependencies) as client:
        resp = client.get("/?param=13")

    assert resp.json() == {
        "detail": "A dependency failed validation for GET http://testserver.local/?param=13",
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
        "detail": "Validation failed for GET http://testserver.local/?param=thirteen",
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
        "detail": "Validation failed for GET http://testserver.local/?param=thirteen",
        "extra": [{"loc": ["param"], "msg": "value is not a valid integer", "type": "type_error.integer"}],
        "status_code": 400,
    }


def test_create_signature_model_error_message(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        SignatureModelFactory, "check_for_unprovided_dependency", MagicMock(side_effect=TypeError("a type error"))
    )

    @get()
    def get_handler(p: int) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException) as e:
        SignatureModelFactory(get_handler.fn.value, [], set()).create_signature_model()

    assert (
        str(e)
        == "<ExceptionInfo 500 - ImproperlyConfiguredException - Error creating signature model for 'get_handler': 'a type error' tblen=2>"
    )


def test_signature_model_resolves_forward_ref_annotations(create_module: "Callable[[str], ModuleType]") -> None:
    module = create_module(
        """
from __future__ import annotations
from pydantic import BaseModel
from starlite import Provide, Starlite, get

class Test(BaseModel):
    hello: str

async def get_dep() -> Test:
    return Test(hello="world")

@get("/", dependencies={"test": Provide(get_dep)})
def hello_world(test: Test) -> Test:
    return test

app = Starlite(route_handlers=[hello_world], openapi_config=None)
"""
    )
    with TestClient(app=module.app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"hello": "world"}
