from __future__ import annotations

from litestar.testing import TestClient


def test_dto_data_problem_statement_app() -> None:
    from docs.examples.plugins.init_plugin_protocol import app

    with TestClient(app) as client:
        assert client.get("/").json() == {"hello": "world"}


def test_openapi_spec_plugin_example() -> None:
    from docs.examples.plugins.openapi_spec_plugin import app

    with TestClient(app) as client:
        resp = client.get("/schema/openapi.json")
        assert resp.status_code == 200
        document = resp.json()

        # The plugin contributed a BearerJWT security scheme.
        assert document["components"]["securitySchemes"]["BearerJWT"] == {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
        # And applied it to every operation as a security requirement.
        assert document["paths"]["/items"]["get"]["security"] == [{"BearerJWT": []}]
