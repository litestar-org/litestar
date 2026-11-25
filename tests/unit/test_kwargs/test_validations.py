# pyright: reportUnnecessaryTypeIgnoreComment=false

from collections.abc import Callable
from typing import Annotated, Any
from unittest.mock import MagicMock

import pytest

from litestar import Litestar, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import (
    BodyKwarg,
    CookieParameter,
    FromPath,
    FromQuery,
    HeaderParameter,
    JSONBody,
    MultipartBody,
    QueryParameter,
    SkipValidation,
    URLEncodedBody,
)
from litestar.testing import create_test_client


def test_path_param_named_like_dependency_key_is_path_param() -> None:
    async def provide_my_key() -> str:
        return "from-dependency"

    @get("/{my_key:str}", dependencies={"my_key": provide_my_key})
    async def handler(my_key: FromPath[str]) -> str:
        return my_key

    with create_test_client([handler]) as client:
        response = client.get("/from-path")

    assert response.text == "from-path"


@pytest.mark.parametrize(
    "annotation, request_kwargs",
    [
        (Annotated[str, QueryParameter(name="my_key")], {"params": {"my_key": "from-request"}}),
        (Annotated[str, HeaderParameter(name="my_key")], {"headers": {"my_key": "from-request"}}),
        (Annotated[str, CookieParameter(name="my_key")], {"headers": {"Cookie": "my_key=from-request"}}),
    ],
)
def test_aliased_param_named_like_dependency_key_is_request_param(
    annotation: Any, request_kwargs: dict[str, Any]
) -> None:
    async def provide_my_key() -> str:
        return "from-dependency"

    @get("/", dependencies={"my_key": provide_my_key})
    async def handler(my_key: annotation) -> str:  # pyright: ignore
        return my_key  # type: ignore[no-any-return]

    with create_test_client([handler]) as client:
        response = client.get("/", **request_kwargs)

    assert response.text == "from-request"


def test_provider_param_named_like_own_key_is_request_param() -> None:
    async def provide_page(page: FromQuery[int]) -> int:
        return page * 2

    @get("/", dependencies={"page": provide_page})
    async def handler(page: NamedDependency[int]) -> int:
        return page

    with create_test_client([handler]) as client:
        response = client.get("/", params={"page": 3})

    assert response.json() == 6


def url_encoded_dependency(data: URLEncodedBody[dict[str, Any]]) -> dict[str, Any]:
    assert data
    return data


def multi_part_dependency(data: MultipartBody[dict[str, Any]]) -> dict[str, Any]:
    assert data
    return data


def json_dependency(data: JSONBody[dict[str, Any]]) -> dict[str, Any]:
    assert data
    return data


@pytest.mark.parametrize(
    "body_annotation, dependency",
    [
        (dict[str, Any], json_dependency),
        (MultipartBody[dict[str, Any]], multi_part_dependency),
        (URLEncodedBody[dict[str, Any]], url_encoded_dependency),
    ],
)
def test_dependency_data_kwarg_validation_success_scenarios(body_annotation: Any, dependency: Callable) -> None:
    @post("/", dependencies={"first": Provide(dependency, sync_to_thread=False)})
    def handler(first: NamedDependency[dict[str, Any]], data: JSONBody[body_annotation]) -> None:  # pyright: ignore
        pass

    Litestar(route_handlers=[handler])


@pytest.mark.parametrize(
    "body_annotation, dependency",
    [
        [Any, json_dependency],
        [Any, url_encoded_dependency],
        [Any, multi_part_dependency],
        [URLEncodedBody[Any], json_dependency],  # type: ignore[misc]
        [URLEncodedBody[Any], multi_part_dependency],  # type: ignore[misc]
        [MultipartBody[Any], json_dependency],  # type: ignore[misc]
        [MultipartBody[Any], url_encoded_dependency],  # type: ignore[misc]
    ],
)
def test_dependency_data_kwarg_validation_failure_scenarios(body_annotation: BodyKwarg, dependency: Callable) -> None:
    @post("/", dependencies={"first": Provide(dependency, sync_to_thread=False)})
    def handler(first: NamedDependency[dict[str, Any]], data: JSONBody[body_annotation]) -> None:  # type: ignore[valid-type]
        assert first
        assert data

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler])


def test_skip_validation() -> None:
    mock = MagicMock()

    @get("/")
    def handler(foo: SkipValidation[FromQuery[int]]) -> None:
        mock(foo)
        return

    with create_test_client([handler]) as client:
        client.get("/?foo=1")

    mock.assert_called_once_with("1")


def test_skip_validation_dependency() -> None:
    mock = MagicMock()

    async def provide_foo() -> str:
        return "1"

    @get("/", dependencies={"foo": provide_foo})
    def handler(foo: NamedDependency[SkipValidation[int]]) -> None:
        mock(foo)
        return

    with create_test_client([handler]) as client:
        client.get("/")

    mock.assert_called_once_with("1")
