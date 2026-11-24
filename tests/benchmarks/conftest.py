from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.benchmarks.helpers import ASGIRunner


@pytest.fixture(scope="session")
def runner() -> Iterator[ASGIRunner]:
    asgi_runner = ASGIRunner()
    yield asgi_runner
    asgi_runner.close()
