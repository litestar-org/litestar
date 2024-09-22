from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import RapidocRenderPlugin, SwaggerRenderPlugin
from litestar.testing import TestClient

rapidoc_fragment = ".addEventListener('before-try',"
swagger_fragment = "requestInterceptor:"


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
        assert rapidoc_fragment in resp.text


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
        assert swagger_fragment in resp.text


def test_plugins_csrf_httponly() -> None:
    app = Litestar(
        csrf_config=CSRFConfig(secret="litestar", cookie_httponly=True),
        openapi_config=OpenAPIConfig(
            title="Litestar Example",
            version="0.0.1",
            render_plugins=[RapidocRenderPlugin(), SwaggerRenderPlugin()],
        ),
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/rapidoc")
        assert resp.status_code == 200
        assert rapidoc_fragment not in resp.text

        resp = client.get("/schema/swagger")
        assert resp.status_code == 200
        assert swagger_fragment not in resp.text
