# pyright: reportUnnecessaryTypeIgnoreComment=false

from collections.abc import Callable
from typing import Annotated, Any
from unittest.mock import MagicMock

import pytest

from litestar import Litestar, get, post, websocket
from litestar.constants import RESERVED_KWARGS
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import (
    BodyKwarg,
    CookieParameter,
    FromQuery,
    HeaderParameter,
    MultipartBody,
    QueryParameter,
    SkipValidation,
    URLEncodedBody,
)
from litestar.testing import create_test_client

_PARAM_TYPES = {"query": QueryParameter, "header": HeaderParameter, "cookie": CookieParameter}


async def my_dependency() -> int:
    return 1


@pytest.mark.parametrize("param_field", ["query", "header", "cookie"])
def test_path_param_and_param_with_same_key_raises(param_field: str) -> None:
    @get("/{my_key:str}")
    def handler(my_key: Annotated[str, _PARAM_TYPES[param_field](name="my_key")]) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Litestar([handler])


def test_path_param_and_dependency_with_same_key_raises() -> None:
    @get("/{my_key:str}", dependencies={"my_key": Provide(my_dependency)})
    def handler(my_key: str) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Litestar([handler])


@pytest.mark.parametrize("param_field", ["query", "header", "cookie"])
def test_dependency_and_aliased_param_raises(param_field: str) -> None:
    @get("/", dependencies={"my_key": Provide(my_dependency)})
    def handler(my_key: Annotated[str, _PARAM_TYPES[param_field](name="my_key")]) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Litestar([handler])


@pytest.mark.parametrize("reserved_kwarg", sorted(RESERVED_KWARGS))
def test_raises_when_reserved_kwargs_are_misused(reserved_kwarg: str) -> None:
    decorator = post if reserved_kwarg != "socket" else websocket
    local = dict(locals(), **globals())
    exec(f"async def test_fn({reserved_kwarg}: int) -> None: pass", local, local)
    handler_with_path_param = decorator("/{" + reserved_kwarg + ":int}")(local["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler_with_path_param])

    exec(f"async def test_fn({reserved_kwarg}: int) -> None: pass", local, local)
    handler_with_dependency = decorator("/", dependencies={reserved_kwarg: Provide(my_dependency)})(local["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler_with_dependency])

    exec(
        f"async def test_fn({reserved_kwarg}: Annotated[int, QueryParameter(name='my_param')]) -> None: pass",
        local,
        local,
    )
    handler_with_aliased_param = decorator("/")(local["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler_with_aliased_param])


def url_encoded_dependency(data: URLEncodedBody[dict[str, Any]]) -> dict[str, Any]:
    assert data
    return data


def multi_part_dependency(data: MultipartBody[dict[str, Any]]) -> dict[str, Any]:
    assert data
    return data


def json_dependency(data: dict[str, Any]) -> dict[str, Any]:
    assert data
    return data


@pytest.mark.parametrize(
    "body_annotation, dependency",
    [
        (Any, json_dependency),
        (MultipartBody[Any], multi_part_dependency),  # type: ignore[misc]
        (URLEncodedBody[Any], url_encoded_dependency),  # type: ignore[misc]
    ],
)
def test_dependency_data_kwarg_validation_success_scenarios(body_annotation: Any, dependency: Callable) -> None:
    @post("/", dependencies={"first": Provide(dependency)})
    def handler(first: NamedDependency[dict[str, Any]], data: body_annotation) -> None:  # pyright: ignore
        pass

    Litestar(route_handlers=[handler])


@pytest.mark.parametrize(
    "body_annotation, dependency",
    [
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
    def handler(first: NamedDependency[dict[str, Any]], data: body_annotation) -> None:  # type: ignore[valid-type]
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
    def handler(foo: SkipValidation[int]) -> None:
        mock(foo)
        return

    with create_test_client([handler]) as client:
        client.get("/")

    mock.assert_called_once_with("1")


@pytest.mark.parametrize(
    "first_param, second_param",
    [
        (QueryParameter(name="field_a"), QueryParameter(name="field_b")),
        (HeaderParameter(name="field-a"), HeaderParameter(name="field-b")),
        (CookieParameter(name="field_a"), CookieParameter(name="field_b")),
        (QueryParameter(name="field"), HeaderParameter(name="field")),
    ],
)
def test_dependencies_with_same_param_name_but_different_source_raises(first_param: Any, second_param: Any) -> None:
    def provide_a(field: Annotated[str, first_param]) -> str:
        return field

    def provide_b(field: Annotated[str, second_param]) -> str:
        return field

    @get(
        "/", dependencies={"a": Provide(provide_a, sync_to_thread=False), "b": Provide(provide_b, sync_to_thread=False)}
    )
    def handler(a: NamedDependency[str], b: NamedDependency[str]) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException, match="'field'"):
        Litestar([handler])


def test_handler_and_dependency_param_with_same_name_but_different_source_raises() -> None:
    def provide_a(field: Annotated[str, QueryParameter(name="field_a")]) -> str:
        return field

    @get("/", dependencies={"a": Provide(provide_a, sync_to_thread=False)})
    def handler(a: NamedDependency[str], field: Annotated[str, QueryParameter(name="field_b")]) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException, match="'field'"):
        Litestar([handler])


def test_dependency_param_overriding_layered_param_with_different_source_raises() -> None:
    def provide_a(field: Annotated[str, QueryParameter(name="field_a")]) -> str:
        return field

    @get("/", dependencies={"a": Provide(provide_a, sync_to_thread=False)})
    def handler(a: NamedDependency[str]) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException, match="'field'"):
        Litestar([handler], parameters={"field": QueryParameter(annotation=str, name="field_b", required=False)})


@pytest.mark.parametrize(
    "first_param, second_param, request_kwargs",
    [
        (QueryParameter(name="field"), QueryParameter(name="field"), {"params": {"field": "x"}}),
        (HeaderParameter(name="X-Field"), HeaderParameter(name="x-field"), {"headers": {"x-field": "x"}}),
    ],
)
def test_dependencies_sharing_the_same_param_do_not_raise(
    first_param: Any, second_param: Any, request_kwargs: dict[str, Any]
) -> None:
    def provide_a(field: Annotated[str, first_param]) -> str:
        return f"a-{field}"

    def provide_b(field: Annotated[str, second_param]) -> str:
        return f"b-{field}"

    @get(
        "/", dependencies={"a": Provide(provide_a, sync_to_thread=False), "b": Provide(provide_b, sync_to_thread=False)}
    )
    def handler(a: NamedDependency[str], b: NamedDependency[str]) -> list[str]:
        return [a, b]

    with create_test_client([handler]) as client:
        assert client.get("/", **request_kwargs).json() == ["a-x", "b-x"]
