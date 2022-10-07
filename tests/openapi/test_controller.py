from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from starlite import OpenAPIConfig
from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.enums import MediaType
from starlite.testing import create_test_client
from tests.openapi.utils import PersonController, PetController
from starlite.openapi.controller import OpenAPIController as _OpenAPIController


class OpenAPIController(_OpenAPIController):
    """
    test class for usage in a couple "offline" tests
    and for without google fonts test
    """
    redoc_google_fonts = False
    redoc_js_url = "https://offline_location/redoc.standalone.js"
    swagger_css_url = "https://offline_location/swagger-ui-css"
    swagger_ui_bundle_js_url = "https://offline_location/swagger-ui-bundle.js"
    swagger_ui_standalone_preset_js_url = "https://offline_location/swagger-ui-standalone-preset.js"
    stoplight_elements_css_url = "https://offline_location/spotlight-styles.mins.css"
    stoplight_elements_js_url = "https://offline_location/spotlight-web-components.min.js"

def test_without_google_fonts() -> None:
    config = OpenAPIConfig(
        title="Starlite API", version="1.0.0", openapi_controller=OpenAPIController)
    with create_test_client([PersonController, PetController], openapi_config=config) as client:
        response = client.get("/schema/redoc")
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
        assert OpenAPIController.swagger_js_ui_bundle in response.text
        assert OpenAPIController.swagger_js_standalone_preset_js in response.text


def test_openapi_stoplight_elements_offline() -> None:
    config = OpenAPIConfig(title="Starlite API", version="1.0.0", openapi_controller=OpenAPIController)
    with create_test_client([PersonController, PetController], openapi_config=config) as client:
        response = client.get("/schema/elements")
        assert OpenAPIController.stoplight_css_url in response.text
        assert OpenAPIController.stoplight_js_url in response.text


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
