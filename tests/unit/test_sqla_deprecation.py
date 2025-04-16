from __future__ import annotations

import re

import pytest


@pytest.mark.parametrize(
    "import_name, module, module_name",
    [
        (
                "SQLAlchemyAsyncRepository",
                "litestar.plugins.sqlalchemy.repository",
                "repository",
        ),
        (
                "SQLAlchemySyncRepository",
                "litestar.plugins.sqlalchemy.repository",
                "repository",
        ),
        ("ModelT", "litestar.plugins.sqlalchemy.repository", "repository"),
        (
                "wrap_sqlalchemy_exception",
                "litestar.plugins.sqlalchemy.exceptions",
                "exceptions",
        ),
    ],
)
def test_sqla_contrib_deprecations(import_name: str, module: str, module_name: str) -> None:
    """Test that importing from litestar.contrib.sqlalchemy raises the correct deprecation warning."""
    parent_path = ".".join(module.split('.')[:-1])
    expected_message = re.escape(
        f"importing {import_name} from 'litestar.contrib.sqlalchemy' is deprecated, please "
        f"import '{module_name}' from '{parent_path}', and call as '{module_name}.{import_name}' instead"
    )

    with pytest.warns(DeprecationWarning, match=expected_message):
        # Import dynamically to trigger the warning within the context manager
        imported_module = __import__("litestar.contrib.sqlalchemy", fromlist=[import_name])
        assert hasattr(imported_module, import_name)
        # Ensure the imported object is not None or some unexpected value
        assert getattr(imported_module, import_name) is not None
