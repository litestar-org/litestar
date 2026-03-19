from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Annotated, Any, Callable, Optional, Union
from unittest.mock import MagicMock

import msgspec
import pytest

from litestar import Litestar, get
from litestar._signature import SignatureModel
from litestar.di import Provide
from litestar.dto import DataclassDTO
from litestar.params import Body, Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT
from litestar.testing import TestClient, create_test_client
from litestar.types import Empty
from litestar.utils.signature import ParsedSignature


def _make_prefixed_decoder(
    target_type: type[Any], prefix: str
) -> tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]:
    def predicate(annotation: Any) -> bool:
        return annotation is target_type

    def decoder(annotation: type[Any], value: Any) -> Any:
        return annotation(f"{prefix}:{value}")

    return predicate, decoder


def _assert_unsupported_query_type(response: Any, key: str = "user_id") -> None:
    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"].startswith("Validation failed for GET")
    assert payload["extra"] == [{"message": "Unsupported type: <class 'str'>", "key": key, "source": "query"}]


def test_create_function_signature_model_parameter_parsing() -> None:
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    model = SignatureModel.create(
        dependency_name_set=set(),
        fn=my_fn.fn,
        data_dto=None,
        parsed_signature=ParsedSignature.from_fn(my_fn.fn, {}),
        type_decoders=[],
    )
    fields = model._fields
    assert fields["a"].annotation is int
    assert not fields["a"].is_optional
    assert fields["b"].annotation is str
    assert not fields["b"].is_optional
    assert fields["c"].annotation is Optional[bytes]
    assert fields["c"].is_optional
    assert fields["c"].default is Empty
    assert fields["d"].annotation is bytes
    assert fields["d"].default == b"123"
    assert fields["e"].annotation == Optional[dict]
    assert fields["e"].is_optional
    assert fields["e"].default is None


def test_create_function_signature_model_ignore_return_annotation() -> None:
    @get(path="/health", status_code=HTTP_204_NO_CONTENT)
    async def health_check() -> None:
        return None

    signature_model_type = SignatureModel.create(
        dependency_name_set=set(),
        fn=health_check.fn,
        data_dto=None,
        parsed_signature=ParsedSignature.from_fn(health_check.fn, {}),
        type_decoders=[],
    )
    assert signature_model_type().to_dict() == {}


def test_signature_model_resolves_forward_ref_annotations(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from msgspec import Struct
from litestar import Litestar, get
from litestar.di import Provide

class Test(Struct):
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
    def test(a: Optional[list[int]] = Parameter(query="a", default=None, required=False)) -> Optional[list[int]]:
        return a

    with create_test_client(route_handlers=[test]) as client:
        response = client.get(f"/{query}")
        assert response.status_code == HTTP_200_OK, response.json()
        assert response.json() == exp


def test_field_definition_is_non_string_iterable() -> None:
    def fn(a: Iterable[int], b: Optional[Iterable[int]]) -> None:
        pass

    model = SignatureModel.create(
        dependency_name_set=set(),
        fn=fn,
        data_dto=None,
        parsed_signature=ParsedSignature.from_fn(fn, {}),
        type_decoders=[],
    )

    assert model._fields["a"].is_non_string_iterable
    assert model._fields["b"].is_non_string_iterable


def test_field_definition_is_non_string_sequence() -> None:
    def fn(a: Sequence[int], b: Optional[Sequence[int]]) -> None:
        pass

    model = SignatureModel.create(
        dependency_name_set=set(),
        fn=fn,
        data_dto=None,
        parsed_signature=ParsedSignature.from_fn(fn, signature_namespace={}),
        type_decoders=[],
    )

    assert model._fields["a"].is_non_string_sequence
    assert model._fields["b"].is_non_string_sequence


@pytest.mark.parametrize("query,expected", [("1", True), ("true", True), ("0", False), ("false", False)])
def test_query_param_bool(query: str, expected: bool) -> None:
    mock = MagicMock()

    @get("/")
    def handler(param: bool) -> None:
        mock(param)

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get(f"/?param={query}")
        assert response.status_code == HTTP_200_OK, response.json()
        mock.assert_called_once_with(expected)


def test_union_constraint_handling() -> None:
    mock = MagicMock()

    @get("/")
    def handler(param: Annotated[Union[str, list[str]], Body(max_length=3, max_items=3)]) -> None:
        mock(param)

    with create_test_client([handler]) as client:
        response = client.get("/?param=foo")

    assert response.status_code == 200
    mock.assert_called_once_with("foo")


@pytest.mark.parametrize(("with_optional",), [(True,), (False,)])
def test_collection_union_struct_fields(with_optional: bool) -> None:
    """Test consistent behavior between optional and non-optional collection unions.

    Issue: https://github.com/litestar-org/litestar/issues/2600 identified that where a union
    of collection types was optional, it would result in a 400 error when the handler was called,
    whereas a non-optional union would result in a 500 error.

    This test ensures that both optional and non-optional unions of collection types result in
    the same error.
    """

    annotation = Union[list[str], list[int]]

    if with_optional:
        annotation = Optional[annotation]  # type: ignore[misc]

    @get("/", signature_namespace={"annotation": annotation})
    def handler(param: annotation) -> None:  # pyright: ignore
        return None

    with create_test_client([handler], debug=True) as client:
        response = client.get("/?param=foo&param=bar&param=123")

    assert response.status_code == 500
    assert "TypeError: Type unions may not contain more than one array-like" in response.text


def test_dto_data_typed_as_any() -> None:
    """DTOs already validate the payload, we don't need the signature model to do it too.

    https://github.com/litestar-org/litestar/issues/2149
    """

    @dataclass
    class Test:
        a: str

    dto = DataclassDTO[Test]

    def fn(data: Test) -> None:
        pass

    model = SignatureModel.create(
        dependency_name_set=set(),
        fn=fn,
        data_dto=dto,
        parsed_signature=ParsedSignature.from_fn(fn, signature_namespace={"Test": Test}),
        type_decoders=[],
    )
    (field,) = msgspec.structs.fields(model)
    assert field.name == "data"
    assert field.type is Any


def test_same_app_type_decoder_does_not_leak_to_handler_without_decoder() -> None:
    class UserId:
        def __init__(self, value: str) -> None:
            self.value = value

    @get("/decoded", type_decoders=[_make_prefixed_decoder(UserId, "decoded")], sync_to_thread=False)
    def decoded(user_id: UserId) -> str:
        return user_id.value

    @get("/plain", sync_to_thread=False)
    def plain(user_id: UserId) -> str:
        return user_id.value

    with create_test_client(route_handlers=[decoded, plain]) as client:
        assert client.get("/decoded?user_id=1").text == "decoded:1"
        _assert_unsupported_query_type(client.get("/plain?user_id=1"))


def test_conflicting_type_decoders_do_not_overwrite_each_other() -> None:
    class UserId:
        def __init__(self, value: str) -> None:
            self.value = value

    @get("/a", type_decoders=[_make_prefixed_decoder(UserId, "handler-a")], sync_to_thread=False)
    def handler_a(user_id: UserId) -> str:
        return user_id.value

    @get("/b", type_decoders=[_make_prefixed_decoder(UserId, "handler-b")], sync_to_thread=False)
    def handler_b(user_id: UserId) -> str:
        return user_id.value

    with create_test_client(route_handlers=[handler_a, handler_b]) as client:
        assert client.get("/a?user_id=1").text == "handler-a:1"
        assert client.get("/b?user_id=1").text == "handler-b:1"

    with create_test_client(route_handlers=[handler_b, handler_a]) as client:
        assert client.get("/a?user_id=1").text == "handler-a:1"
        assert client.get("/b?user_id=1").text == "handler-b:1"


def test_type_decoder_does_not_leak_across_apps() -> None:
    class UserId:
        def __init__(self, value: str) -> None:
            self.value = value

    @get("/", type_decoders=[_make_prefixed_decoder(UserId, "app-a")], sync_to_thread=False)
    def app_a_handler(user_id: UserId) -> str:
        return user_id.value

    @get("/", sync_to_thread=False)
    def app_b_handler(user_id: UserId) -> str:
        return user_id.value

    app_a = Litestar([app_a_handler], openapi_config=None)
    app_b = Litestar([app_b_handler], openapi_config=None)

    with TestClient(app_a) as client:
        assert client.get("/?user_id=1").text == "app-a:1"

    with TestClient(app_b) as client:
        _assert_unsupported_query_type(client.get("/?user_id=1"))

    with TestClient(app_a) as client:
        assert client.get("/?user_id=2").text == "app-a:2"


def test_provider_signature_model_decoder_does_not_leak() -> None:
    class UserId:
        def __init__(self, value: str) -> None:
            self.value = value

    async def provide_token(user_id: UserId) -> str:
        return user_id.value

    @get(
        "/provided",
        dependencies={"token": Provide(provide_token)},
        type_decoders=[_make_prefixed_decoder(UserId, "provider")],
        sync_to_thread=False,
    )
    def provided(token: str) -> str:
        return token

    @get("/plain", sync_to_thread=False)
    def plain(user_id: UserId) -> str:
        return user_id.value

    with create_test_client(route_handlers=[provided, plain]) as client:
        assert client.get("/provided?user_id=1").text == "provider:1"
        _assert_unsupported_query_type(client.get("/plain?user_id=1"))


def test_signature_model_creation_does_not_mutate_user_type() -> None:
    class UserId:
        def __init__(self, value: str) -> None:
            self.value = value

    def fn(user_id: UserId) -> None:
        pass

    SignatureModel.create(
        dependency_name_set=set(),
        fn=fn,
        data_dto=None,
        parsed_signature=ParsedSignature.from_fn(fn, {}),
        type_decoders=[_make_prefixed_decoder(UserId, "model")],
    )

    assert not hasattr(UserId, "_decoder")
