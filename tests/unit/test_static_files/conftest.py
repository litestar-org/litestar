from __future__ import annotations

import pytest
from _pytest.fixtures import FixtureRequest
from fsspec.implementations.local import LocalFileSystem

from litestar.file_system import BaseLocalFileSystem, maybe_wrap_fsspec_file_system
from litestar.types import BaseFileSystem


@pytest.fixture(params=[BaseLocalFileSystem(), LocalFileSystem()])
def file_system(request: FixtureRequest) -> BaseFileSystem:
    return maybe_wrap_fsspec_file_system(request.param)
