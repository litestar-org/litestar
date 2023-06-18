import pytest

from litestar import Litestar, get
from litestar.exceptions import ImproperlyConfiguredException


async def first_method(query_param: int) -> int:
    return query_param


async def second_method(path_param: str) -> str:
    return path_param


def test_dependency_validation() -> None:
    @get(
        path="/{path_param:int}",
        dependencies={"first": first_method, "second": second_method},
    )
    def handler(first: int, second: str, third: int) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[handler], dependencies={"third": first_method})
