import logging
import os
from typing import Generator

import pytest


@pytest.fixture()
def reset_httpx_logging() -> Generator[None, None, None]:
    # ensure that httpx logging is not interfering with our test client
    httpx_logger = logging.getLogger("httpx")
    initial_level = httpx_logger.level
    httpx_logger.setLevel(logging.WARNING)
    yield
    httpx_logger.setLevel(initial_level)


# the monkeypatch fixture does not work with session scoped dependencies
@pytest.fixture(autouse=True, scope="session")
def disable_warn_implicit_sync_to_thread() -> Generator[None, None, None]:
    old_value = os.getenv("LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD")
    os.environ["LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD"] = "0"
    yield
    if old_value is not None:
        os.environ["LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD"] = old_value
