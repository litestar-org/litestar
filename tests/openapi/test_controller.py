from starlite import OpenAPIConfig
from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.enums import MediaType
from starlite.openapi.controller import OpenAPIController as _OpenAPIController
from starlite.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from starlite.testing import create_test_client
from tests.openapi.utils import PersonController, PetController


class OpenAPIController(_OpenAPIController):
    """test class for usage in a couple "offline" tests and for without Google
    fonts test."""

    redoc_google_fonts = False
    redoc_js_url = "https://offline_location/redoc.standalone.js"
    swagger_css_url = "https://offline_location/swagger-ui-css"
    swagger_ui_bundle_js_url = "https://offline_location/swagger-ui-bundle.js"
    swagger_ui_standalone_preset_js_url = "https://offline_location/swagger-ui-standalone-preset.js"
    stoplight_elements_css_url = "https://offline_location/spotlight-styles.mins.css"
    stoplight_elements_js_url = "https://offline_location/spotlight-web-components.min.js"


def test_default_redoc_cdn_urls() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema/redoc")
        default_redoc_version = "next"
        default_redoc_js_bundle = (
            f"https://cdn.jsdelivr.net/npm/redoc@{default_redoc_version}/bundles/redoc.standalone.js"
        )
        assert client.app.openapi_config is not None
        assert client.app.openapi_config.openapi_controller.redoc_js_url == default_redoc_js_bundle
        assert default_redoc_js_bundle in response.text


def test_default_swagger_ui_cdn_urls() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema/swagger")
        default_swagger_ui_version = "4.14.0"
        default_swagger_bundles = [
            f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{default_swagger_ui_version}/swagger-ui.css",
            f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{default_swagger_ui_version}/swagger-ui-bundle.js",
            f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{default_swagger_ui_version}/swagger-ui-standalone-preset.js",
        ]
        assert client.app.openapi_config is not None
        assert client.app.openapi_config.openapi_controller.swagger_css_url in default_swagger_bundles
        assert client.app.openapi_config.openapi_controller.swagger_ui_bundle_js_url in default_swagger_bundles
        assert (
            client.app.openapi_config.openapi_controller.swagger_ui_standalone_preset_js_url in default_swagger_bundles
        )
        assert all(cdn_url in response.text for cdn_url in default_swagger_bundles)


def test_default_stoplight_elements_cdn_urls() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema/elements")
        default_stoplight_elements_version = "7.6.5"
        default_stoplight_elements_bundles = [
            f"https://unpkg.com/@stoplight/elements@{default_stoplight_elements_version}/styles.min.css",
            f"https://unpkg.com/@stoplight/elements@{default_stoplight_elements_version}/web-components.min.js",
        ]
        assert client.app.openapi_config is not None
        assert (
            client.app.openapi_config.openapi_controller.stoplight_elements_css_url
            in default_stoplight_elements_bundles
        )
        assert (
            client.app.openapi_config.openapi_controller.stoplight_elements_js_url in default_stoplight_elements_bundles
        )
        assert all(cdn_url in response.text for cdn_url in default_stoplight_elements_bundles)


def test_redoc_with_google_fonts() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema/redoc")
        google_font_cdn = "https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700"
        assert client.app.openapi_config is not None
        assert client.app.openapi_config.openapi_controller.redoc_google_fonts is True
        assert google_font_cdn in response.text


def test_redoc_without_google_fonts() -> None:
    config = OpenAPIConfig(title="Starlite API", version="1.0.0", openapi_controller=OpenAPIController)
    with create_test_client([PersonController, PetController], openapi_config=config) as client:
        response = client.get("/schema/redoc")
        assert config.openapi_controller.redoc_google_fonts is False
        assert "fonts.googleapis.com" not in response.text


def test_openapi_redoc_offline() -> None:
    config = OpenAPIConfig(title="Starlite API", version="1.0.0", openapi_controller=OpenAPIController)
    with create_test_client([PersonController, PetController], openapi_config=config) as client:
        response = client.get("/schema/redoc")
        assert OpenAPIController.redoc_js_url in response.text
        assert "fonts.googleapis.com" not in response.text


def test_openapi_swagger_offline() -> None:
    config = OpenAPIConfig(title="Starlite API", version="1.0.0", openapi_controller=OpenAPIController)
    with create_test_client([PersonController, PetController], openapi_config=config) as client:
        response = client.get("/schema/swagger")
        assert OpenAPIController.swagger_css_url in response.text
        assert OpenAPIController.swagger_ui_bundle_js_url in response.text
        assert OpenAPIController.swagger_ui_standalone_preset_js_url in response.text


def test_openapi_stoplight_elements_offline() -> None:
    config = OpenAPIConfig(title="Starlite API", version="1.0.0", openapi_controller=OpenAPIController)
    with create_test_client([PersonController, PetController], openapi_config=config) as client:
        response = client.get("/schema/elements")
        assert OpenAPIController.stoplight_elements_css_url in response.text
        assert OpenAPIController.stoplight_elements_js_url in response.text


def test_openapi_root() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_redoc() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema/redoc")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_swagger() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema/swagger")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_stoplight_elements() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema/elements/")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_root_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard(DEFAULT_OPENAPI_CONFIG.root_schema_site)

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        response = client.get("/schema")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_redoc_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard("redoc")

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        response = client.get("/schema/redoc")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_swagger_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard("swagger")

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        response = client.get("/schema/swagger")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_stoplight_elements_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard("elements")

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        response = client.get("/schema/elements/")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)
