from __future__ import annotations

from litestar.handlers import get
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import JsonRenderPlugin
from litestar.testing import create_test_client


def test_openapi_json() -> None:
    @get("/test")
    def get_handler() -> str:
        return "test"

    with create_test_client(
        [get_handler], openapi_config=OpenAPIConfig(title="Test", version="1.0.0", render_plugins=[JsonRenderPlugin()])
    ) as client:
        response = client.get("/schema/openapi.json")
        assert response.status_code == 200
        assert response.json() == {
            "info": {"title": "Test", "version": "1.0.0"},
            "openapi": "3.1.0",
            "servers": [{"url": "/"}],
            "paths": {
                "/test": {
                    "get": {
                        "summary": "GetHandler",
                        "operationId": "TestGetHandler",
                        "responses": {
                            "200": {
                                "description": "Request fulfilled, document follows",
                                "headers": {},
                                "content": {"text/plain": {"schema": {"type": "string"}}},
                            }
                        },
                        "deprecated": False,
                    }
                }
            },
            "components": {"schemas": {}},
        }
