from typing import Any, Callable, Dict

import pytest
from pydantic.fields import FieldInfo

from litestar import Litestar, get, post, websocket
from litestar.constants import RESERVED_KWARGS, SKIP_VALIDATION_NAMES
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers.http_handlers import HTTPRouteHandler
from litestar.params import Body, Parameter


async def my_dependency() -> int:
    return 1


@get("/{my_key:str}")
def handler_with_path_param_and_aliased_query_parameter_collision(my_key: str = Parameter(query="my_key")) -> None:
    ...


@get("/{my_key:str}")
def handler_with_path_param_and_aliased_header_parameter_collision(my_key: str = Parameter(header="my_key")) -> None:
    ...


@get("/{my_key:str}")
def handler_with_path_param_and_aliased_cookie_parameter_collision(my_key: str = Parameter(cookie="my_key")) -> None:
    ...


@get("/{my_key:str}", dependencies={"my_key": Provide(my_dependency)})
def handler_with_path_param_dependency_collision(my_key: str) -> None:
    ...


@get("/", dependencies={"my_key": Provide(my_dependency)})
def handler_with_dependency_and_aliased_query_parameter_collision(my_key: str = Parameter(query="my_key")) -> None:
    ...


@get("/", dependencies={"my_key": Provide(my_dependency)})
def handler_with_dependency_and_aliased_header_parameter_collision(my_key: str = Parameter(header="my_key")) -> None:
    ...


@get("/", dependencies={"my_key": Provide(my_dependency)})
def handler_with_dependency_and_aliased_cookie_parameter_collision(my_key: str = Parameter(cookie="my_key")) -> None:
    ...


@pytest.mark.parametrize(
    "handler",
    [
        handler_with_path_param_and_aliased_query_parameter_collision,
        handler_with_path_param_and_aliased_header_parameter_collision,
        handler_with_path_param_and_aliased_cookie_parameter_collision,
        handler_with_path_param_dependency_collision,
        handler_with_dependency_and_aliased_query_parameter_collision,
        handler_with_dependency_and_aliased_header_parameter_collision,
        handler_with_dependency_and_aliased_cookie_parameter_collision,
    ],
)
def test_raises_exception_when_keys_are_ambiguous(handler: HTTPRouteHandler) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler])


@pytest.mark.parametrize("reserved_kwarg", RESERVED_KWARGS)
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

    # these kwargs are set to Any when the signature model is generated,
    # because pydantic can't handle generics for non pydantic classes. So these tests won't work for aliased parameters.
    if reserved_kwarg not in SKIP_VALIDATION_NAMES:
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


@post("/", dependencies={"first": Provide(json_dependency, sync_to_thread=True)})
def accepted_json_handler(data: Dict[str, Any], first: Dict[str, Any]) -> None:
    assert data
    assert first


@post("/", dependencies={"first": Provide(url_encoded_dependency, sync_to_thread=True)})
def accepted_url_encoded_handler(
    first: Dict[str, Any],
    data: Dict[str, Any] = Body(media_type=RequestEncodingType.URL_ENCODED),
) -> None:
    assert data
    assert first


@post("/", dependencies={"first": Provide(multi_part_dependency, sync_to_thread=True)})
def accepted_multi_part_handler(
    first: Dict[str, Any],
    data: Dict[str, Any] = Body(media_type=RequestEncodingType.MULTI_PART),
) -> None:
    assert data
    assert first


@pytest.mark.parametrize("handler", [accepted_json_handler, accepted_url_encoded_handler, accepted_multi_part_handler])
def test_dependency_data_kwarg_validation_success_scenarios(handler: HTTPRouteHandler) -> None:
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
def test_dependency_data_kwarg_validation_failure_scenarios(body: FieldInfo, dependency: Callable) -> None:
    @post("/", dependencies={"first": Provide(dependency, sync_to_thread=False)})
    def handler(first: Dict[str, Any], data: Any = body) -> None:
        assert first
        assert data

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler])
