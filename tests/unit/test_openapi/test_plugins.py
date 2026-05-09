import pytest

from litestar import Litestar
from litestar._openapi.plugin import merge_openapi_components
from litestar.config.csrf import CSRFConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import RapidocRenderPlugin, ScalarRenderPlugin, SwaggerRenderPlugin
from litestar.openapi.spec import Components, OAuthFlow, OAuthFlows, OpenAPIType, Reference, Schema, SecurityScheme
from litestar.plugins import OpenAPISpecPlugin
from litestar.testing import TestClient

rapidoc_fragment = ".addEventListener('before-try',"
swagger_fragment = "requestInterceptor:"


def _bearer_scheme() -> SecurityScheme:
    return SecurityScheme(type="http", scheme="bearer", bearer_format="JWT")


def _oauth_scheme() -> SecurityScheme:
    return SecurityScheme(
        type="oauth2",
        flows=OAuthFlows(
            password=OAuthFlow(token_url="/token", scopes={"read": "read scope"}),
        ),
    )


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


def test_swagger_ui_oauth2_redirect_url() -> None:
    redirect_url = "https://example.com/api/v1/schema/oauth2-redirect.html"
    app = Litestar(
        openapi_config=OpenAPIConfig(
            title="Litestar Example",
            version="0.0.1",
            render_plugins=[SwaggerRenderPlugin(oauth2_redirect_url=redirect_url)],
        ),
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/swagger")
        assert resp.status_code == 200
        assert f"oauth2RedirectUrl: '{redirect_url}'" in resp.text


def test_swagger_ui_oauth2_redirect_url_unset() -> None:
    """When oauth2_redirect_url is not set, Swagger UI computes it from the page URL (default behaviour)."""
    app = Litestar(
        openapi_config=OpenAPIConfig(
            title="Litestar Example",
            version="0.0.1",
            render_plugins=[SwaggerRenderPlugin()],
        ),
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/swagger")
        assert resp.status_code == 200
        assert "oauth2RedirectUrl" not in resp.text


@pytest.mark.parametrize(
    "scalar_config",
    [
        {"showSidebar": False},
    ],
)
@pytest.mark.parametrize(
    "expected_config_render",
    [
        "document.getElementById('api-reference').dataset.configuration = '{\"showSidebar\":false}'",
    ],
)
def test_openapi_scalar_options(scalar_config: dict, expected_config_render: str) -> None:
    app = Litestar(
        openapi_config=OpenAPIConfig(
            title="Litestar Example",
            version="0.0.1",
            render_plugins=[ScalarRenderPlugin(options=scalar_config)],
        )
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/scalar")
        assert resp.status_code == 200
        assert expected_config_render in resp.text


# ---------------------------------------------------------------------------
# OpenAPISpecPlugin contributions: merge_openapi_components helper + wire-up
# ---------------------------------------------------------------------------


def test_merge_openapi_components_empty_target_copies_source_dict() -> None:
    """An empty (``None``) target field is populated with a *copy* of the source dict."""
    target = Components()
    source = Components(security_schemes={"bearer": _bearer_scheme()})

    merge_openapi_components(target, source)

    assert source.security_schemes is not None
    assert target.security_schemes == {"bearer": source.security_schemes["bearer"]}
    # The merged dict is independent of the source: mutating it does not leak.
    assert target.security_schemes is not None
    target.security_schemes["other"] = _oauth_scheme()
    assert "other" not in source.security_schemes


def test_merge_openapi_components_populated_target_last_wins() -> None:
    """Existing keys on the target are overwritten by the source on collision; non-colliding keys merge."""
    target_bearer = _bearer_scheme()
    source_bearer = SecurityScheme(type="http", scheme="bearer", bearer_format="OPAQUE")
    target = Components(security_schemes={"bearer": target_bearer, "session": _oauth_scheme()})
    source = Components(security_schemes={"bearer": source_bearer, "api_key": _bearer_scheme()})

    merge_openapi_components(target, source)

    assert target.security_schemes is not None
    assert target.security_schemes["bearer"] is source_bearer  # last-wins on collision
    assert "session" in target.security_schemes  # untouched key from target
    assert "api_key" in target.security_schemes  # new key added from source


def test_merge_openapi_components_none_source_field_skipped() -> None:
    """``None``/falsy source fields contribute nothing and leave the target untouched."""
    bearer = _bearer_scheme()
    target = Components(security_schemes={"bearer": bearer})
    source = Components()  # all dict fields default to None / empty

    merge_openapi_components(target, source)

    assert target.security_schemes == {"bearer": bearer}
    # Nothing else got initialized as a side effect.
    assert target.responses is None
    assert target.parameters is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("schemas", {"Foo": Schema(title="Foo")}),
        ("security_schemes", {"bearer": _bearer_scheme()}),
        ("parameters", {"X": Reference(ref="#/x")}),
    ],
)
def test_merge_openapi_components_per_field(field_name: str, value: dict) -> None:
    """Every dict-valued :class:`Components` field is mergeable through the helper."""
    target = Components()
    source = Components(**{field_name: value})

    merge_openapi_components(target, source)

    assert getattr(target, field_name) == value


def test_openapi_spec_plugin_contributed_components_appear_in_document() -> None:
    """A registered ``OpenAPISpecPlugin`` returning :class:`Components` has them merged into the served document."""

    class BearerContributor(OpenAPISpecPlugin):
        def get_openapi_components(self) -> Components:
            return Components(security_schemes={"BearerJWT": _bearer_scheme()})

    app = Litestar(
        plugins=[BearerContributor()],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/openapi.json")
        assert resp.status_code == 200
        components = resp.json()["components"]
        assert "BearerJWT" in components["securitySchemes"]
        assert components["securitySchemes"]["BearerJWT"]["type"] == "http"


def test_openapi_spec_plugin_multiple_contributors_last_wins_on_collision() -> None:
    """When two plugins contribute the same component key, the later registration wins."""

    class First(OpenAPISpecPlugin):
        def get_openapi_components(self) -> Components:
            return Components(security_schemes={"shared": _bearer_scheme()})

    class Second(OpenAPISpecPlugin):
        def get_openapi_components(self) -> Components:
            return Components(security_schemes={"shared": _oauth_scheme()})

    app = Litestar(
        plugins=[First(), Second()],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/openapi.json")
        assert resp.status_code == 200
        assert resp.json()["components"]["securitySchemes"]["shared"]["type"] == "oauth2"


def test_openapi_spec_plugin_components_layered_non_auth_contributions() -> None:
    """Components layering with non-auth fragments: shared schemas + reusable parameters.

    Two plugins contribute different :class:`Components` fields (``schemas`` from one,
    ``parameters`` from another). Both end up merged into the served document. A third
    contributor collides on a key already present and wins last.
    """

    class ProblemDetailsPlugin(OpenAPISpecPlugin):
        def get_openapi_components(self) -> Components:
            return Components(schemas={"ProblemDetails": Schema(title="ProblemDetails", type=OpenAPIType.OBJECT)})

    class TracingHeaderPlugin(OpenAPISpecPlugin):
        def get_openapi_components(self) -> Components:
            return Components(
                parameters={"X-Request-Id": Reference(ref="#/components/parameters/X-Request-Id")},
            )

    class ProblemDetailsOverridePlugin(OpenAPISpecPlugin):
        def get_openapi_components(self) -> Components:
            return Components(schemas={"ProblemDetails": Schema(title="ProblemDetails", description="overridden")})

    app = Litestar(
        plugins=[ProblemDetailsPlugin(), TracingHeaderPlugin(), ProblemDetailsOverridePlugin()],
        openapi_config=OpenAPIConfig(title="t", version="0.0.1"),
    )

    with TestClient(app=app) as client:
        resp = client.get("/schema/openapi.json")
        assert resp.status_code == 200
        components = resp.json()["components"]

    # First plugin's schema is present, but the third plugin's collision overrode the value.
    assert components["schemas"]["ProblemDetails"] == {
        "title": "ProblemDetails",
        "description": "overridden",
    }
    # Independent contributions from different plugins coexist.
    assert components["parameters"]["X-Request-Id"] == {"$ref": "#/components/parameters/X-Request-Id"}
