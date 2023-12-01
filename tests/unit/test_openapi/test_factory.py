from __future__ import annotations

import pytest

from litestar import Litestar
from litestar.exceptions import ImproperlyConfiguredException


def test_factory_openapi_config_raises_if_not_configured() -> None:
    app = Litestar(openapi_config=None)
    with pytest.raises(ImproperlyConfiguredException):
        app._openapi_factory.openapi_config


def test_factory_openapi_paths_raise_if_none() -> None:
    app = Litestar()
    assert app.openapi_config is not None
    app._openapi_factory.openapi_schema.paths = None
    with pytest.raises(ImproperlyConfiguredException):
        app._openapi_factory.paths
