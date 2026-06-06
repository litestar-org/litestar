from typing import List, Set

import pytest

from litestar._kwargs.dependencies import DependencyContainer, create_dependency_batches
from litestar.di import NamedDependency, Provide
from litestar.exceptions import HTTPException, ValidationException
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
    dependency_tree: Set[DependencyContainer], expected_batches: List[Set[DependencyContainer]]
) -> None:
    calculated_batches = create_dependency_batches(dependency_tree)
    assert calculated_batches == expected_batches


@pytest.mark.parametrize(
    "exception,status_code,text",
    [
        (ValueError("value_error"), HTTP_500_INTERNAL_SERVER_ERROR, "Exception Group Traceback"),
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
