import pytest

from starlite import ImproperlyConfiguredException, Parameter, Provide, Starlite, get


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
def test_raises_exception_when_keys_are_ambigous(handler):
    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler])
