from typing import Any, Callable, Dict

import pytest
from typing_extensions import Annotated

from litestar import Litestar, get, post, websocket
from litestar.constants import RESERVED_KWARGS
from litestar.di import Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import (
    BodyKwarg,
    CookieParameter,
    HeaderParameter,
    MultipartBody,
    QueryParameter,
    URLEncodedBody,
)

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


def url_encoded_dependency(data: URLEncodedBody[Dict[str, Any]]) -> Dict[str, Any]:
    assert data
    return data


def multi_part_dependency(data: MultipartBody[Dict[str, Any]]) -> Dict[str, Any]:
    assert data
    return data


def json_dependency(data: Dict[str, Any]) -> Dict[str, Any]:
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
    def handler(first: Dict[str, Any], data: body_annotation) -> None:
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
    def handler(first: Dict[str, Any], data: body_annotation) -> None:  # type: ignore[valid-type]
        assert first
        assert data

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler])
