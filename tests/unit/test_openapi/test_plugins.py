from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import RapidocRenderPlugin, SwaggerRenderPlugin
from litestar.testing import TestClient


def test_rapidoc_csrf() -> None:
    app = Litestar(
        csrf_config=CSRFConfig(secret="litestar"),
        openapi_config=OpenAPIConfig(
            title="Litestar Example",
            version="0.0.1",
            render_plugins=[RapidocRenderPlugin()],
        ),
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/rapidoc")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert ".addEventListener('before-try'," in resp.text


def test_swagger_ui_csrf() -> None:
    app = Litestar(
        csrf_config=CSRFConfig(secret="litestar"),
        openapi_config=OpenAPIConfig(
            title="Litestar Example",
            version="0.0.1",
            render_plugins=[SwaggerRenderPlugin()],
        ),
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/swagger")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "requestInterceptor:" in resp.text
