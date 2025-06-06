import importlib.util
import sys
from pathlib import Path
from typing import List, Union

import pytest
from advanced_alchemy import repository as advanced_alchemy_repo


def purge_module(module_names: List[str], path: Union[str, Path]) -> None:
    """Remove modules from sys.modules and delete the corresponding .pyc cache file.

    This ensures that modules are freshly imported in tests, which is important
    when testing import behavior.

    Args:
        module_names: List of module names to purge
        path: Path to the source file
    """
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(importlib.util.cache_from_source(path)).unlink(missing_ok=True)  # type: ignore[arg-type]


def test_direct_import_from_plugins_sqlalchemy_repository() -> None:
    """Test that SQLAlchemyAsyncRepository can be imported directly from litestar.plugins.sqlalchemy.repository."""
    purge_module(["litestar.plugins.sqlalchemy.repository"], __file__)

    # This should work with our fix
    from litestar.plugins.sqlalchemy.repository import SQLAlchemyAsyncRepository

    assert SQLAlchemyAsyncRepository is advanced_alchemy_repo.SQLAlchemyAsyncRepository


def test_import_from_contrib_sqlalchemy_repository() -> None:
    """Test that SQLAlchemyAsyncRepository can be imported from litestar.contrib.sqlalchemy.repository."""
    purge_module(["litestar.contrib.sqlalchemy.repository"], __file__)

    # This should continue to work as before
    with pytest.warns(
        DeprecationWarning,
        match="importing SQLAlchemyAsyncRepository from 'litestar.contrib.sqlalchemy.repository' is deprecated",
    ):
        from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository

    assert SQLAlchemyAsyncRepository is advanced_alchemy_repo.SQLAlchemyAsyncRepository


def test_import_repository_module_from_plugins_sqlalchemy() -> None:
    """Test that the repository module can be imported from litestar.plugins.sqlalchemy."""
    purge_module(["litestar.plugins.sqlalchemy"], __file__)

    # This should work through the redirect in sqlalchemy.py
    from litestar.plugins.sqlalchemy import repository

    assert repository.SQLAlchemyAsyncRepository is advanced_alchemy_repo.SQLAlchemyAsyncRepository
    assert repository.SQLAlchemySyncRepository is advanced_alchemy_repo.SQLAlchemySyncRepository


def test_direct_import_from_plugins_sqlalchemy() -> None:
    """Test that SQLAlchemyAsyncRepository can be imported directly from litestar.plugins.sqlalchemy."""
    purge_module(["litestar.plugins.sqlalchemy"], __file__)

    # This should also work through the redirect
    from litestar.plugins.sqlalchemy import SQLAlchemyAsyncRepository

    assert SQLAlchemyAsyncRepository is advanced_alchemy_repo.SQLAlchemyAsyncRepository
