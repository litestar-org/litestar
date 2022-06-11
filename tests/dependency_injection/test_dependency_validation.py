from typing import Generic, TypeVar

import pytest

from starlite import ImproperlyConfiguredException, Provide, Starlite, get


def first_method(query_param: int) -> int:
    assert isinstance(query_param, int)
    return query_param


def second_method(path_param: str) -> str:
    assert isinstance(path_param, str)
    return path_param


def test_dependency_validation() -> None:
    @get(
        path="/{path_param:int}",
        dependencies={
            "first": Provide(first_method),
            "second": Provide(second_method),
        },
    )
    def test_function(first: int, second: str, third: int) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(
            route_handlers=[test_function],
            dependencies={
                "third": Provide(first_method),
            },
        )


@pytest.mark.xfail  # type:ignore[misc]
def test_create_schema_generic_type_field() -> None:
    T = TypeVar("T")

    class GenericType(Generic[T]):
        t: T

    @get("/")
    def handler_function(dep: GenericType[int]) -> None:
        ...

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler_function])
