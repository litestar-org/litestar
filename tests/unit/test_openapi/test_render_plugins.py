from __future__ import annotations

from litestar.openapi.plugins import OpenAPIRenderPlugin
from litestar.testing import RequestFactory


def test_render_plugin_get_openapi_json_route() -> None:
    request = RequestFactory(root_path="/root").get()
    assert OpenAPIRenderPlugin.get_openapi_json_route(request) == "/schema/openapi.json"
