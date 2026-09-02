from collections import Counter
from typing import Any, cast

import pytest

from litestar import Litestar
from litestar._kwargs.dependencies import DependencyContainer, create_dependency_batches, create_dependency_graph
from litestar._kwargs.kwargs_model import KwargsModel
from litestar.di import NamedDependency, Provide
from litestar.exceptions import HTTPException, ImproperlyConfiguredException, ValidationException
from litestar.handlers import get
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import create_test_client


async def dummy() -> None:
    pass


DEPENDENCY_A = DependencyContainer("A", Provide(dummy), [])
DEPENDENCY_B = DependencyContainer("B", Provide(dummy), [])
DEPENDENCY_C1 = DependencyContainer("C1", Provide(dummy), [])
DEPENDENCY_C2 = DependencyContainer("C2", Provide(dummy), [DEPENDENCY_C1])
DEPENDENCY_ALL_EXCEPT_A = DependencyContainer("D", Provide(dummy), [DEPENDENCY_B, DEPENDENCY_C1, DEPENDENCY_C2])


@pytest.mark.parametrize(
    "dependency_tree,expected_batches",
    [
        (set(), []),
        ({DEPENDENCY_A}, [{DEPENDENCY_A}]),
        (
            {DEPENDENCY_A, DEPENDENCY_B},
            [
                {DEPENDENCY_A, DEPENDENCY_B},
            ],
        ),
        (
            {DEPENDENCY_C1, DEPENDENCY_C2},
            [
                {DEPENDENCY_C1},
                {DEPENDENCY_C2},
            ],
        ),
        (
            {DEPENDENCY_A, DEPENDENCY_B, DEPENDENCY_C1, DEPENDENCY_C2, DEPENDENCY_ALL_EXCEPT_A},
            [
                {DEPENDENCY_A, DEPENDENCY_B, DEPENDENCY_C1},
                {DEPENDENCY_C2},
                {DEPENDENCY_ALL_EXCEPT_A},
            ],
        ),
        (
            {DEPENDENCY_ALL_EXCEPT_A},
            [
                {DEPENDENCY_B, DEPENDENCY_C1},
                {DEPENDENCY_C2},
                {DEPENDENCY_ALL_EXCEPT_A},
            ],
        ),
    ],
)
def test_dependency_batches(
    dependency_tree: set[DependencyContainer], expected_batches: list[set[DependencyContainer]]
) -> None:
    calculated_batches = create_dependency_batches(dependency_tree)
    assert calculated_batches == expected_batches


def test_dependency_graph_reuses_shared_nodes() -> None:
    async def shared() -> int:
        return 1

    async def left(shared: NamedDependency[int]) -> int:
        return shared

    async def right(shared: NamedDependency[int]) -> int:
        return shared

    dependencies = {"shared": Provide(shared), "left": Provide(left), "right": Provide(right)}

    @get(path="/", dependencies=dependencies)
    async def handler(left: NamedDependency[int], right: NamedDependency[int]) -> int:
        return left + right

    Litestar(route_handlers=[handler], openapi_config=None)
    graph = create_dependency_graph(dependency_keys=("left", "right"), dependencies=dependencies)

    assert set(graph.nodes) == {"shared", "left", "right"}
    assert graph.nodes["left"].dependencies[0] is graph.nodes["shared"]
    assert graph.nodes["right"].dependencies[0] is graph.nodes["shared"]


def test_dependency_signature_metadata_is_created_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: Counter[int] = Counter()
    original = cast("Any", KwargsModel._create_signature_metadata).__func__

    def track_metadata(cls: type[KwargsModel], *args: Any, **kwargs: Any) -> Any:
        signature_model = kwargs["signature_model"]
        calls[id(signature_model)] += 1
        return original(cls, *args, **kwargs)

    monkeypatch.setattr(KwargsModel, "_create_signature_metadata", classmethod(track_metadata))

    async def first() -> int:
        return 1

    async def second(first: NamedDependency[int]) -> int:
        return first

    async def third(first: NamedDependency[int], second: NamedDependency[int]) -> int:
        return first + second

    async def fourth(first: NamedDependency[int], second: NamedDependency[int], third: NamedDependency[int]) -> int:
        return first + second + third

    @get(path="/")
    async def handler(fourth: NamedDependency[int]) -> int:
        return fourth

    dependencies = {
        "first": Provide(first),
        "second": Provide(second),
        "third": Provide(third),
        "fourth": Provide(fourth),
    }
    Litestar(
        route_handlers=[handler],
        dependencies=dependencies,
        openapi_config=None,
    )

    assert all(calls[id(provider.signature_model)] == 1 for provider in dependencies.values())


def test_dependency_cycle_raises_configuration_error() -> None:
    async def first(second: NamedDependency[int]) -> int:
        return second

    async def second(first: NamedDependency[int]) -> int:
        return first

    @get(path="/")
    async def handler(first: NamedDependency[int]) -> int:
        return first

    with pytest.raises(ImproperlyConfiguredException, match="Dependency cycle detected: first -> second -> first"):
        Litestar(
            route_handlers=[handler],
            dependencies={"first": Provide(first), "second": Provide(second)},
            openapi_config=None,
        )


@pytest.mark.parametrize(
    "exception,status_code,text",
    [
        (ValueError("value_error"), HTTP_500_INTERNAL_SERVER_ERROR, "500 - Internal Server Error"),
        (
            HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="http_exception"),
            HTTP_422_UNPROCESSABLE_ENTITY,
            '{"status_code":422,"detail":"http_exception"}',
        ),
        (
            ValidationException("validation_exception"),
            HTTP_400_BAD_REQUEST,
            '{"status_code":400,"detail":"validation_exception"}',
        ),
    ],
)
def test_dependency_batch_with_exception(exception: Exception, status_code: int, text: str) -> None:
    def a() -> None:
        raise exception

    def c(a: NamedDependency[None], b: NamedDependency[None]) -> None:
        pass

    @get(path="/")
    def handler(c: NamedDependency[None]) -> None:
        pass

    with create_test_client(
        route_handlers=handler,
        dependencies={
            "a": Provide(a),
            "b": Provide(dummy),
            "c": Provide(c),
        },
    ) as client:
        response = client.get("/")

    assert response.status_code == status_code
    assert text in response.text
