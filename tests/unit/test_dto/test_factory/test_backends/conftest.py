import pytest

from litestar.dto._backend import DTOBackend
from litestar.dto._codegen_backend import DTOCodegenBackend


@pytest.fixture()
def backend_cls(use_experimental_dto_backend: bool) -> type[DTOBackend | DTOCodegenBackend]:
    if use_experimental_dto_backend:
        return DTOCodegenBackend
    return DTOBackend
