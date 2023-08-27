import importlib

import pytest


@pytest.mark.parametrize(
    "import_path, import_name",
    (
        (
            "litestar.contrib.repository",
            "AbstractAsyncRepository",
        ),
        (
            "litestar.contrib.repository",
            "AbstractSyncRepository",
        ),
        (
            "litestar.contrib.repository",
            "ConflictError",
        ),
        (
            "litestar.contrib.repository",
            "FilterTypes",
        ),
        (
            "litestar.contrib.repository",
            "NotFoundError",
        ),
        (
            "litestar.contrib.repository",
            "RepositoryError",
        ),
        (
            "litestar.contrib.repository.exceptions",
            "ConflictError",
        ),
        (
            "litestar.contrib.repository.exceptions",
            "NotFoundError",
        ),
        (
            "litestar.contrib.repository.exceptions",
            "RepositoryError",
        ),
        (
            "litestar.contrib.repository.filters",
            "BeforeAfter",
        ),
        (
            "litestar.contrib.repository.filters",
            "CollectionFilter",
        ),
        (
            "litestar.contrib.repository.filters",
            "FilterTypes",
        ),
        (
            "litestar.contrib.repository.filters",
            "LimitOffset",
        ),
        (
            "litestar.contrib.repository.filters",
            "OrderBy",
        ),
        (
            "litestar.contrib.repository.filters",
            "SearchFilter",
        ),
        (
            "litestar.contrib.repository.filters",
            "NotInCollectionFilter",
        ),
        (
            "litestar.contrib.repository.filters",
            "OnBeforeAfter",
        ),
        (
            "litestar.contrib.repository.filters",
            "NotInSearchFilter",
        ),
        (
            "litestar.contrib.repository.handlers",
            "signature_namespace_values",
        ),
        (
            "litestar.contrib.repository.handlers",
            "on_app_init",
        ),
        (
            "litestar.contrib.repository.testing",
            "GenericAsyncMockRepository",
        ),
    ),
)
def test_repository_deprecations(import_path: str, import_name: str) -> None:
    module = importlib.import_module(import_path)
    assert getattr(module, import_name)
