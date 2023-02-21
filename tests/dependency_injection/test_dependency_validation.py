import pytest

from starlite import Starlite, get
from starlite.di import Provide
from starlite.exceptions import ImproperlyConfiguredException


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
            "second": Provide(second_method, sync_to_thread=True),
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


def test_raises_when_dependency_is_not_callable() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Provide(123)  # type: ignore
