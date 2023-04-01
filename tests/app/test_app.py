from __future__ import annotations

import pytest

from litestar import Litestar
from litestar.exceptions import ImproperlyConfiguredException


def test_access_openapi_schema_raises_if_not_configured() -> None:
    """Test that accessing the openapi schema raises if not configured."""
    app = Litestar(openapi_config=None)
    with pytest.raises(ImproperlyConfiguredException):
        app.openapi_schema
