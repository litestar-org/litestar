import pytest

from starlite import (
    ImproperlyConfiguredException,
    Parameter,
    Provide,
    Starlite,
    get,
    post,
)
from starlite.constants import RESERVED_KWARGS


def my_dependency() -> int:
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
def test_raises_exception_when_keys_are_ambiguous(handler):
    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler])


@pytest.mark.parametrize("reserved_kwarg", [kwarg for kwarg in RESERVED_KWARGS if kwarg not in ["socket", "request"]])
def test_raises_when_reserved_kwargs_are_misused(reserved_kwarg):
    exec(f"def test_fn({reserved_kwarg}: int) -> None: pass")
    handler_with_path_param = post("/{" + reserved_kwarg + ":int}")(locals()["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler_with_path_param])

    exec(f"def test_fn({reserved_kwarg}: int) -> None: pass")
    handler_with_dependency = post("/", dependencies={reserved_kwarg: Provide(my_dependency)})(locals()["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler_with_dependency])

    exec(f"def test_fn({reserved_kwarg}: int = Parameter(query='my_param')) -> None: pass")
    handler_with_aliased_param = post("/")(locals()["test_fn"])
    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler_with_aliased_param])
