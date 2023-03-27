from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from examples.plugins.sqlalchemy_init_plugin.sqlalchemy_async import app as async_sqla_app
from examples.plugins.sqlalchemy_init_plugin.sqlalchemy_sync import app as sync_sqla_app
from starlite.testing import TestClient

if TYPE_CHECKING:
    from starlite import Starlite


@pytest.mark.parametrize("app", [async_sqla_app, sync_sqla_app])
def test_app(app: Starlite) -> None:
    with TestClient(app=app) as client:
        res = client.get("/sqlalchemy-app")
        assert res.status_code == 200
        assert res.json() == "1 2"
