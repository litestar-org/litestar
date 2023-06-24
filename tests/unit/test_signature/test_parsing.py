from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, Iterable, List, Literal, Optional, Sequence
from unittest.mock import MagicMock

import pytest
from attr import define
from pydantic import BaseModel
from typing_extensions import TypedDict

from litestar import get, post
from litestar._signature import create_signature_model
from litestar.di import Provide
from litestar.exceptions import ImproperlyConfiguredException, ValidationException
from litestar.params import Dependency, Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import RequestFactory, TestClient, create_test_client
from litestar.types.helper_types import OptionalSequence
from litestar.utils.signature import ParsedSignature


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_parses_values_from_connection_kwargs_without_plugin(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    class MyModel(BaseModel):
        name: str

    def fn(a: MyModel) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        parsed_signature=ParsedSignature.from_fn(fn, {}),
    )
    result = model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a={"name": "my name"})
    assert result == {"a": MyModel(name="my name")}


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_parses_values_from_connection_kwargs_raises(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    def fn(a: int) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        parsed_signature=ParsedSignature.from_fn(fn, {}),
    )
    with pytest.raises(ValidationException):
        model.parse_values_from_connection_kwargs(connection=RequestFactory().get(), a="not an int")


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_create_function_signature_model_parameter_parsing(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    model = create_signature_model(
        fn=my_fn.fn.value,
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        parsed_signature=ParsedSignature.from_fn(my_fn.fn.value, {}),
    )
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
    assert fields["e"].field_type == Optional[dict]
    assert fields["e"].is_optional
    assert fields["e"].default_value is None


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_create_signature_validation(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    @get()
    def my_fn(typed: int, untyped) -> None:  # type: ignore
        pass

    with pytest.raises(ImproperlyConfiguredException):
        create_signature_model(
            fn=my_fn.fn.value,
            dependency_name_set=set(),
            preferred_validation_backend=preferred_validation_backend,
            parsed_signature=ParsedSignature.from_fn(my_fn.fn.value, {}),
        )


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_create_function_signature_model_ignore_return_annotation(
    preferred_validation_backend: Literal["attrs", "pydantic"]
) -> None:
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return None

    signature_model_type = create_signature_model(
        fn=health_check.fn.value,
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        parsed_signature=ParsedSignature.from_fn(health_check.fn.value, {}),
    )
    assert signature_model_type().to_dict() == {}


@pytest.mark.parametrize(
    "preferred_validation_backend, error_extra",
    (
        (
            "attrs",
            [{"key": "dep", "message": "invalid literal for int() with base 10: 'thirteen'"}],
        ),
        (
            "pydantic",
            [{"key": "dep", "message": "value is not a valid integer"}],
        ),
    ),
)
def test_dependency_validation_failure_raises_500(
    preferred_validation_backend: Literal["attrs", "pydantic"],
    error_extra: Any,
) -> None:
    dependencies = {"dep": Provide(lambda: "thirteen", sync_to_thread=False)}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(
        route_handlers=[test], dependencies=dependencies, _preferred_validation_backend=preferred_validation_backend
    ) as client:
        response = client.get("/?param=13")

    assert response.json() == {
        "detail": "Internal Server Error",
        "extra": error_extra,
        "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
    }


@pytest.mark.parametrize(
    "preferred_validation_backend, error_extra",
    (
        (
            "attrs",
            [{"key": "param", "message": "invalid literal for int() with base 10: 'thirteen'", "source": "query"}],
        ),
    ),
)
def test_validation_failure_raises_400(
    preferred_validation_backend: Literal["attrs", "pydantic"], error_extra: Any
) -> None:
    dependencies = {"dep": Provide(lambda: 13, sync_to_thread=False)}

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(
        route_handlers=[test], dependencies=dependencies, _preferred_validation_backend=preferred_validation_backend
    ) as client:
        response = client.get("/?param=thirteen")

    assert response.json() == {
        "detail": "Validation failed for GET http://testserver.local/?param=thirteen",
        "extra": error_extra,
        "status_code": 400,
    }


def test_client_pydantic_backend_error_precedence_over_server_error() -> None:
    dependencies = {
        "dep": Provide(lambda: "thirteen", sync_to_thread=False),
        "optional_dep": Provide(lambda: "thirty-one", sync_to_thread=False),
    }

    @get("/")
    def test(dep: int, param: int, optional_dep: Optional[int] = Dependency()) -> None:
        ...

    with create_test_client(
        route_handlers=[test], dependencies=dependencies, _preferred_validation_backend="pydantic"
    ) as client:
        response = client.get("/?param=thirteen")

    assert response.json() == {
        "detail": "Validation failed for GET http://testserver.local/?param=thirteen",
        "extra": [{"key": "param", "message": "value is not a valid integer", "source": "query"}],
        "status_code": 400,
    }


def test_signature_model_resolves_forward_ref_annotations(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from pydantic import BaseModel
from litestar import Litestar, get
from litestar.di import Provide

class Test(BaseModel):
    hello: str

async def get_dep() -> Test:
    return Test(hello="world")

@get("/", dependencies={"test": Provide(get_dep)})
def hello_world(test: Test) -> Test:
    return test

app = Litestar(route_handlers=[hello_world], openapi_config=None)
"""
    )
    with TestClient(app=module.app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"hello": "world"}


@pytest.mark.parametrize(("query", "exp"), [("?a=1&a=2&a=3", [1, 2, 3]), ("", None)])
def test_parse_optional_sequence_from_connection_kwargs(query: str, exp: Any) -> None:
    @get("/")
    def test(a: Optional[List[int]] = Parameter(query="a", default=None, required=False)) -> Optional[List[int]]:
        return a

    with create_test_client(route_handlers=[test]) as client:
        response = client.get(f"/{query}")
        assert response.status_code == HTTP_200_OK, response.json()
        assert response.json() == exp


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_signature_field_is_non_string_iterable(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    def fn(a: Iterable[int], b: Optional[Iterable[int]]) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        parsed_signature=ParsedSignature.from_fn(fn, {}),
    )

    assert model.fields["a"].is_non_string_iterable
    assert model.fields["b"].is_non_string_iterable


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_signature_field_is_non_string_sequence(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    def fn(a: Sequence[int], b: OptionalSequence[int]) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        parsed_signature=ParsedSignature.from_fn(fn, signature_namespace={}),
    )

    assert model.fields["a"].is_non_string_sequence
    assert model.fields["b"].is_non_string_sequence


@pytest.mark.parametrize("signature_backend", ["pydantic", "attrs"])
@pytest.mark.parametrize("query,expected", [("1", True), ("true", True), ("0", False), ("false", False)])
def test_query_param_bool(query: str, expected: bool, signature_backend: Literal["pydantic", "attrs"]) -> None:
    mock = MagicMock()

    @get("/")
    def handler(param: bool) -> None:
        mock(param)

    with create_test_client(route_handlers=[handler], _preferred_validation_backend=signature_backend) as client:
        response = client.get(f"/?param={query}")
        assert response.status_code == HTTP_200_OK, response.json()
        mock.assert_called_once_with(expected)


@pytest.mark.parametrize("preferred_validation_backend", ("attrs", "pydantic"))
def test_validation_error_exception_key(preferred_validation_backend: Literal["attrs", "pydantic"]) -> None:
    class OtherChild(BaseModel):
        val: List[int]

    class Child(BaseModel):
        val: int
        other_val: int

    class Parent(BaseModel):
        child: Child
        other_child: OtherChild

    def fn(model: Parent) -> None:
        pass

    model = create_signature_model(
        fn=fn,
        dependency_name_set=set(),
        preferred_validation_backend=preferred_validation_backend,
        parsed_signature=ParsedSignature.from_fn(fn, {}),
    )

    with pytest.raises(ValidationException) as exc_info:
        model.parse_values_from_connection_kwargs(
            connection=RequestFactory().get(), model={"child": {}, "other_child": {}}
        )

    assert isinstance(exc_info.value.extra, list)
    assert exc_info.value.extra[0]["key"] == "model.child.val"
    assert exc_info.value.extra[1]["key"] == "model.child.other_val"
    assert exc_info.value.extra[2]["key"] == "model.other_child.val"


def test_invalid_input_pydantic() -> None:
    class OtherChild(BaseModel):
        val: List[int]

    class Child(BaseModel):
        val: int
        other_val: int

    class Parent(BaseModel):
        child: Child
        other_child: OtherChild

    @post("/")
    def test(
        data: Parent,
        int_param: int,
        length_param: str = Parameter(min_length=2),
        int_header: int = Parameter(header="X-SOME-INT"),
        int_cookie: int = Parameter(cookie="int-cookie"),
    ) -> None:
        ...

    with create_test_client(route_handlers=[test]) as client:
        response = client.post(
            "/",
            json={"child": {"val": "a", "other_val": "b"}, "other_child": {"val": [1, "c"]}},
            params={"int_param": "param", "length_param": "d"},
            headers={"X-SOME-INT": "header"},
            cookies={"int-cookie": "cookie"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        data = response.json()

        assert data
        assert data["extra"] == [
            {"key": "child.val", "message": "value is not a valid integer", "source": "body"},
            {"key": "child.other_val", "message": "value is not a valid integer", "source": "body"},
            {"key": "other_child.val.1", "message": "value is not a valid integer", "source": "body"},
            {"key": "int_param", "message": "value is not a valid integer", "source": "query"},
            {"key": "length_param", "message": "ensure this value has at least 2 characters", "source": "query"},
            {"key": "int_header", "message": "value is not a valid integer", "source": "header"},
            {"key": "int_cookie", "message": "value is not a valid integer", "source": "cookie"},
        ]


def test_invalid_input_attrs() -> None:
    @define
    class OtherChild:
        val: List[int]

    @define
    class Child:
        val: int
        other_val: int

    @define
    class Parent:
        child: Child
        other_child: OtherChild

    @post("/")
    def test(
        data: Parent,
        int_param: int,
        int_header: int = Parameter(header="X-SOME-INT"),
        int_cookie: int = Parameter(cookie="int-cookie"),
    ) -> None:
        ...

    with create_test_client(route_handlers=[test]) as client:
        response = client.post(
            "/",
            json={"child": {"val": "a", "other_val": "b"}, "other_child": {"val": [1, "c"]}},
            params={"int_param": "param"},
            headers={"X-SOME-INT": "header"},
            cookies={"int-cookie": "cookie"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        data = response.json()

        assert data
        assert data["extra"] == [
            {"key": "child.val", "message": "invalid literal for int() with base 10: 'a'", "source": "body"},
            {"key": "child.other_val", "message": "invalid literal for int() with base 10: 'b'", "source": "body"},
            {"key": "other_child.val.1", "message": "invalid literal for int() with base 10: 'c'", "source": "body"},
            {"key": "int_param", "message": "invalid literal for int() with base 10: 'param'", "source": "query"},
            {"key": "int_header", "message": "invalid literal for int() with base 10: 'header'", "source": "header"},
            {"key": "int_cookie", "message": "invalid literal for int() with base 10: 'cookie'", "source": "cookie"},
        ]


def test_invalid_input_dataclass() -> None:
    @dataclass
    class OtherChild:
        val: List[int]

    @dataclass
    class Child:
        val: int
        other_val: int

    @dataclass
    class Parent:
        child: Child
        other_child: OtherChild

    @post("/")
    def test(
        data: Parent,
        int_param: int,
        length_param: str = Parameter(min_length=2),
        int_header: int = Parameter(header="X-SOME-INT"),
        int_cookie: int = Parameter(cookie="int-cookie"),
    ) -> None:
        ...

    with create_test_client(route_handlers=[test]) as client:
        response = client.post(
            "/",
            json={"child": {"val": "a", "other_val": "b"}, "other_child": {"val": [1, "c"]}},
            params={"int_param": "param", "length_param": "d"},
            headers={"X-SOME-INT": "header"},
            cookies={"int-cookie": "cookie"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        data = response.json()

        assert data
        assert data["extra"] == [
            {"key": "child.val", "message": "value is not a valid integer", "source": "body"},
            {"key": "child.other_val", "message": "value is not a valid integer", "source": "body"},
            {"key": "other_child.val.1", "message": "value is not a valid integer", "source": "body"},
            {"key": "int_param", "message": "value is not a valid integer", "source": "query"},
            {"key": "length_param", "message": "ensure this value has at least 2 characters", "source": "query"},
            {"key": "int_header", "message": "value is not a valid integer", "source": "header"},
            {"key": "int_cookie", "message": "value is not a valid integer", "source": "cookie"},
        ]


def test_invalid_input_typed_dict() -> None:
    class OtherChild(TypedDict):
        val: List[int]

    class Child(TypedDict):
        val: int
        other_val: int

    class Parent(TypedDict):
        child: Child
        other_child: OtherChild

    @post("/")
    def test(
        data: Parent,
        int_param: int,
        length_param: str = Parameter(min_length=2),
        int_header: int = Parameter(header="X-SOME-INT"),
        int_cookie: int = Parameter(cookie="int-cookie"),
    ) -> None:
        ...

    with create_test_client(route_handlers=[test]) as client:
        response = client.post(
            "/",
            json={"child": {"val": "a", "other_val": "b"}, "other_child": {"val": [1, "c"]}},
            params={"int_param": "param", "length_param": "d"},
            headers={"X-SOME-INT": "header"},
            cookies={"int-cookie": "cookie"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        data = response.json()

        assert data
        assert data["extra"] == [
            {"key": "child.val", "message": "value is not a valid integer", "source": "body"},
            {"key": "child.other_val", "message": "value is not a valid integer", "source": "body"},
            {"key": "other_child.val.1", "message": "value is not a valid integer", "source": "body"},
            {"key": "int_param", "message": "value is not a valid integer", "source": "query"},
            {"key": "length_param", "message": "ensure this value has at least 2 characters", "source": "query"},
            {"key": "int_header", "message": "value is not a valid integer", "source": "header"},
            {"key": "int_cookie", "message": "value is not a valid integer", "source": "cookie"},
        ]
