# pyright: reportUnnecessaryTypeIgnoreComment=false

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Annotated, Any, Optional, Union
from unittest.mock import MagicMock

import pytest

from litestar import get, post
from litestar.dto import DataclassDTO
from litestar.params import FromQuery, JSONBody, QueryParameter
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from litestar.testing import TestClient, create_test_client
from litestar.types import Empty
from litestar.utils.signature import ParsedSignature


def test_parsed_signature_parameter_parsing() -> None:
    @get()
    def my_fn(a: int, b: str, c: Optional[bytes], d: bytes = b"123", e: Optional[dict] = None) -> None:
        pass

    fields = ParsedSignature.from_fn(my_fn.fn, {}).parameters
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


def test_signature_model_resolves_forward_ref_annotations(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from __future__ import annotations

from msgspec import Struct
from litestar import Litestar, get
from litestar.di import NamedDependency, Provide

class Test(Struct):
    hello: str

async def get_dep() -> Test:
    return Test(hello="world")

@get("/", dependencies={"test": Provide(get_dep)})
def hello_world(test: NamedDependency[Test]) -> Test:
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
    def test(a: Annotated[Optional[list[int]], QueryParameter(name="a", required=False)] = None) -> Optional[list[int]]:
        return a

    with create_test_client(route_handlers=[test]) as client:
        response = client.get(f"/{query}")
        assert response.status_code == HTTP_200_OK, response.json()
        assert response.json() == exp


def test_field_definition_is_non_string_iterable() -> None:
    def fn(a: Iterable[int], b: Optional[Iterable[int]]) -> None:
        pass

    fields = ParsedSignature.from_fn(fn, {}).parameters

    assert fields["a"].is_non_string_iterable
    assert fields["b"].is_non_string_iterable


def test_field_definition_is_non_string_sequence() -> None:
    def fn(a: Sequence[int], b: Optional[Sequence[int]]) -> None:
        pass

    fields = ParsedSignature.from_fn(fn, signature_namespace={}).parameters

    assert fields["a"].is_non_string_sequence
    assert fields["b"].is_non_string_sequence


@pytest.mark.parametrize("query,expected", [("1", True), ("true", True), ("0", False), ("false", False)])
def test_query_param_bool(query: str, expected: bool) -> None:
    mock = MagicMock()

    @get("/")
    def handler(param: FromQuery[bool]) -> None:
        mock(param)

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get(f"/?param={query}")
        assert response.status_code == HTTP_200_OK, response.json()
        mock.assert_called_once_with(expected)


def test_union_constraint_handling() -> None:
    mock = MagicMock()

    @get("/")
    def handler(param: Annotated[Union[str, list[str]], QueryParameter(max_length=3, max_items=3)]) -> None:
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

    annotation = FromQuery[annotation]  # type: ignore[misc]

    @get("/", signature_namespace={"annotation": annotation})
    def handler(param: annotation) -> None:  # pyright: ignore[reportInvalidTypeForm]
        return None

    with create_test_client([handler], debug=True) as client:
        response = client.get("/?param=foo&param=bar&param=123")

    assert response.status_code == 500
    assert "TypeError: Type unions may not contain more than one array-like" in response.text


def test_dto_data_not_validated_again() -> None:
    """DTOs already validate the payload, the request parameter validation doesn't do it too.

    https://github.com/litestar-org/litestar/issues/2149
    """

    @dataclass
    class Test:
        a: str

    class DTO(DataclassDTO[Test]):
        def decode_bytes(self, value: bytes) -> Any:
            return {"a": 1}

    @post("/", dto=DTO, return_dto=None)
    async def handler(data: JSONBody[Test]) -> Any:
        return data

    with create_test_client([handler]) as client:
        response = client.post("/", json={})

    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"a": 1}
