from __future__ import annotations

import pytest

from litestar.dto._backend import DTOBackend
from litestar.dto._codegen_backend import DTOCodegenBackend


@pytest.fixture()
def backend_cls(use_experimental_dto_backend: bool) -> type[DTOBackend | DTOCodegenBackend]:
    return DTOCodegenBackend if use_experimental_dto_backend else DTOBackend
