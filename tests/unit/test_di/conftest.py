import functools
from pathlib import Path

import pytest

from tests.unit.test_di.helpers import (
    ENTRY_POINTS,
    CallWithDependencies,
    Resolve,
    call_with_dependencies_through,
    resolve_through,
)

HERE = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if HERE in item.path.parents:
            item.add_marker(pytest.mark.timeout(5))


@pytest.fixture(params=ENTRY_POINTS)
def resolve(request: pytest.FixtureRequest) -> Resolve:
    """Resolve a key in a context, once through each public entry point."""
    return functools.partial(resolve_through, request.param)


@pytest.fixture(params=ENTRY_POINTS)
def call_with_dependencies(request: pytest.FixtureRequest) -> CallWithDependencies:
    """Call a callable with its dependencies resolved, once through each public entry point."""
    return functools.partial(call_with_dependencies_through, request.param)
