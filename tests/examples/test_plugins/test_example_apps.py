from __future__ import annotations

from litestar.testing import TestClient


def test_dto_data_problem_statement_app() -> None:
    from docs.examples.plugins.init_plugin_protocol import app

    with TestClient(app) as client:
        assert client.get("/").json() == {"hello": "world"}
