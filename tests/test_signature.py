from functools import lru_cache
from typing import TYPE_CHECKING, Any, List, Optional, Set, Type, cast

import pytest
from pydantic import BaseModel, ValidationError
from pydantic.error_wrappers import ErrorWrapper
from starlette.datastructures import URL
from starlette.status import HTTP_204_NO_CONTENT

from starlite import ImproperlyConfiguredException, Provide, get
from starlite.connection import WebSocket
from starlite.exceptions import InternalServerException, ValidationException
from starlite.params import Dependency
from starlite.signature import SignatureModel, SignatureModelFactory
from starlite.testing import create_test_client, create_test_request
from tests.plugins.test_base import AModel, APlugin

if TYPE_CHECKING:
    from pydantic.error_wrappers import ErrorDict
    from pydantic.typing import AnyCallable

    from starlite.plugins.base import PluginProtocol


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
    arbitary_a = {"name": 1}
    result = model.parse_values_from_connection_kwargs(connection=create_test_request(), a=arbitary_a, b=1)
    assert result == {"a": AModel(name="1"), "b": 1}


def test_parses_values_from_connection_kwargs_without_plugin() -> None:
    class MyModel(BaseModel):
        name: str

    def fn(a: MyModel) -> None:
        pass

    model = make_signature_model(fn)
    result = model.parse_values_from_connection_kwargs(connection=create_test_request(), a={"name": "my name"})
    assert result == {"a": MyModel(name="my name")}


def test_parses_values_from_connection_kwargs_raises() -> None:
    def fn(a: int) -> None:
        pass

    model = make_signature_model(fn)
    with pytest.raises(ValidationException):
        model.parse_values_from_connection_kwargs(connection=create_test_request(), a="not an int")


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
    request = create_test_request()
    errors = [ErrorWrapper(Exception(), loc) for loc in loc_errors]
    validation_error = ValidationError(errors=errors, model=BaseModel)
    exc = model.construct_exception(connection=request, exc=validation_error)

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
        obj = cast(Any, object())
        scope = {"type": "websocket", "path": "/", "headers": []}
        web_socket: WebSocket[Any, Any] = WebSocket(scope=scope, receive=obj, send=obj)
        assert SignatureModel.get_connection_method_and_url(web_socket) == ("websocket", URL("/"))

    def test_request(self) -> None:
        request = create_test_request()
        assert SignatureModel.get_connection_method_and_url(request) == (request.method, request.url)


def test_create_function_signature_model_parameter_parsing() -> None:
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    model = SignatureModelFactory(my_fn.fn, [], set()).create_signature_model()  # type: ignore[arg-type]
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
        SignatureModelFactory(my_fn.fn, [], set()).create_signature_model()  # type: ignore[arg-type]


def test_create_function_signature_model_ignore_return_annotation() -> None:
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return

    signature_model_type = SignatureModelFactory(
        health_check.fn, [], set()  # type:ignore[arg-type]
    ).create_signature_model()
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
