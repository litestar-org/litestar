from typing import Any, Callable, Dict

import pytest

from litestar import Litestar, get, post, websocket
from litestar.constants import RESERVED_KWARGS
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import Body, BodyKwarg, Parameter


async def my_dependency() -> int:
    return 1


@pytest.mark.parametrize("param_field", ["query", "header", "cookie"])
def test_path_param_and_param_with_same_key_raises(param_field: str) -> None:
    @get("/{my_key:str}")
    def handler(my_key: str = Parameter(**{param_field: "my_key"})) -> None:  # type: ignore[arg-type]
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
    def handler(my_key: str = Parameter(**{param_field: "my_key"})) -> None:  # type: ignore[arg-type]
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Litestar([handler])


@pytest.mark.parametrize("reserved_kwarg", sorted(RESERVED_KWARGS))
def test_raises_when_reserved_kwargs_are_misused(reserved_kwarg: str) -> None:
    decorator = post if reserved_kwarg != "socket" else websocket

    exec(f"async def test_fn({reserved_kwarg}: int) -> None: pass")
    handler_with_path_param = decorator("/{" + reserved_kwarg + ":int}")(locals()["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler_with_path_param])

    exec(f"async def test_fn({reserved_kwarg}: int) -> None: pass")
    handler_with_dependency = decorator("/", dependencies={reserved_kwarg: Provide(my_dependency)})(locals()["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler_with_dependency])

    exec(f"async def test_fn({reserved_kwarg}: int = Parameter(query='my_param')) -> None: pass")
    handler_with_aliased_param = decorator("/")(locals()["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler_with_aliased_param])


def url_encoded_dependency(data: Dict[str, Any] = Body(media_type=RequestEncodingType.URL_ENCODED)) -> Dict[str, Any]:
    assert data
    return data


def multi_part_dependency(data: Dict[str, Any] = Body(media_type=RequestEncodingType.MULTI_PART)) -> Dict[str, Any]:
    assert data
    return data


def json_dependency(data: Dict[str, Any] = Body()) -> Dict[str, Any]:
    assert data
    return data


@pytest.mark.parametrize(
    "body, dependency",
    [
        (Body(), json_dependency),
        (Body(media_type=RequestEncodingType.MULTI_PART), multi_part_dependency),
        (Body(media_type=RequestEncodingType.URL_ENCODED), url_encoded_dependency),
    ],
)
def test_dependency_data_kwarg_validation_success_scenarios(body: BodyKwarg, dependency: Callable) -> None:
    @post("/", dependencies={"first": Provide(dependency)})
    def handler(first: Dict[str, Any], data: Any = body) -> None:
        pass

    Litestar(route_handlers=[handler])


@pytest.mark.parametrize(
    "body, dependency",
    [
        [Body(), url_encoded_dependency],
        [Body(), multi_part_dependency],
        [Body(media_type=RequestEncodingType.URL_ENCODED), json_dependency],
        [Body(media_type=RequestEncodingType.URL_ENCODED), multi_part_dependency],
        [Body(media_type=RequestEncodingType.MULTI_PART), json_dependency],
        [Body(media_type=RequestEncodingType.MULTI_PART), url_encoded_dependency],
    ],
)
def test_dependency_data_kwarg_validation_failure_scenarios(body: BodyKwarg, dependency: Callable) -> None:
    @post("/", dependencies={"first": Provide(dependency, sync_to_thread=False)})
    def handler(first: Dict[str, Any], data: Any = body) -> None:
        assert first
        assert data

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler])
