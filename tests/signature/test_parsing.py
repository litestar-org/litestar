import inspect
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Sequence

import pytest
from pydantic import BaseModel

from starlite import get
from starlite._signature import create_signature_model
from starlite._signature.parsing import ParsedSignatureParameter
from starlite.di import Provide
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.params import Dependency, Parameter
from starlite.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT
from starlite.testing import RequestFactory, TestClient, create_test_client
from starlite.types.helper_types import OptionalSequence
from tests.test_plugins import AModel, APlugin

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Callable

    from starlite._signature.models import PydanticSignatureModel


def test_parses_values_from_connection_kwargs_with_plugin() -> None:
    def fn(a: AModel, b: int) -> None:
        pass

    model = create_signature_model(fn, plugins=[APlugin()], dependency_name_set=set(), signature_namespace={})
    arbitrary_a = {"name": 1}
    result = model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a=arbitrary_a, b=1)
    assert result == {"a": AModel(name="1"), "b": 1}


def test_parses_values_from_connection_kwargs_without_plugin() -> None:
    class MyModel(BaseModel):
        name: str

    def fn(a: MyModel) -> None:
        pass

    model = create_signature_model(fn, [], set(), signature_namespace={})
    result = model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a={"name": "my name"})
    assert result == {"a": MyModel(name="my name")}


def test_parses_values_from_connection_kwargs_raises() -> None:
    def fn(a: int) -> None:
        pass

    model = create_signature_model(fn, [], set(), signature_namespace={})
    with pytest.raises(ValidationException):
        model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a="not an int")


def test_resolve_field_value() -> None:
    def fn(a: AModel, b: int) -> None:
        pass

    model: Any = create_signature_model(fn, [APlugin()], set(), signature_namespace={})
    instance: "PydanticSignatureModel" = model(a={"name": "my name"}, b=2)
    assert instance._resolve_field_value("a") == AModel(name="my name")
    assert instance._resolve_field_value("b") == 2


def test_create_function_signature_model_parameter_parsing() -> None:
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    model = create_signature_model(my_fn.fn.value, [], set(), signature_namespace={})
    fields = model.fields
    assert fields["a"].field_type is int
    assert not fields["a"].is_optional
    assert fields["b"].field_type is str
    assert not fields["b"].is_optional
    assert fields["c"].field_type is Optional[bytes]
    assert fields["c"].is_optional
    assert fields["c"].default_value is None
    assert fields["d"].field_type is bytes
    assert fields["d"].default_value == b"123"
    assert fields["e"].field_type is Optional[dict]
    assert fields["e"].is_optional
    assert fields["e"].default_value is None


def test_create_signature_validation() -> None:
    @get()
    def my_fn(typed: int, untyped) -> None:  # type: ignore
        pass

    with pytest.raises(ImproperlyConfiguredException):
        create_signature_model(my_fn.fn.value, [], set(), signature_namespace={})


def test_create_function_signature_model_ignore_return_annotation() -> None:
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return None

    signature_model_type = create_signature_model(health_check.fn.value, [], set(), signature_namespace={})
    assert signature_model_type().to_dict() == {}


def test_create_function_signature_model_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        create_signature_model(lru_cache(maxsize=0)(lambda x: x), [], set(), signature_namespace={}).dict()  # type: ignore


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


def test_signature_model_resolves_forward_ref_annotations(create_module: "Callable[[str], ModuleType]") -> None:
    module = create_module(
        """
from __future__ import annotations

from pydantic import BaseModel
from starlite import Starlite, get
from starlite.di import Provide

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


@pytest.mark.parametrize(("query", "exp"), [("?a=1&a=2&a=3", [1, 2, 3]), ("", None)])
def test_parse_optional_sequence_from_connection_kwargs(query: str, exp: Any) -> None:
    @get("/")
    def test(a: Optional[List[int]] = Parameter(query="a", default=None, required=False)) -> Optional[List[int]]:
        return a

    with create_test_client(route_handlers=[test]) as client:
        resp = client.get(f"/{query}")

    assert resp.status_code == HTTP_200_OK
    assert resp.json() == exp


def test_signature_field_is_non_string_iterable() -> None:
    def fn(a: Iterable[int], b: Optional[Iterable[int]]) -> None:
        pass

    model = create_signature_model(fn, plugins=[], dependency_name_set=set(), signature_namespace={})

    assert model.fields["a"].is_non_string_iterable
    assert model.fields["b"].is_non_string_iterable


def test_signature_field_is_non_string_sequence() -> None:
    def fn(a: Sequence[int], b: OptionalSequence[int]) -> None:
        pass

    model = create_signature_model(fn, plugins=[], dependency_name_set=set(), signature_namespace={})

    assert model.fields["a"].is_non_string_sequence
    assert model.fields["b"].is_non_string_sequence


def test_parsed_signature_model_from_parameter_resolves_forward_ref() -> None:
    def func(a: "int") -> None:
        ...

    signature = inspect.Signature.from_callable(func)
    obj = object()
    parsed_param = ParsedSignatureParameter.from_parameter("func", "a", signature.parameters["a"], {"a": obj})
    assert parsed_param.annotation is obj
