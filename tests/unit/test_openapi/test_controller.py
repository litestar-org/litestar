from typing import List, Type

import pytest

from litestar import Controller
from litestar.enums import MediaType
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.controller import OpenAPIController
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client

root_paths: List[str] = ["", "/part1", "/part1/part2"]


def test_default_redoc_cdn_urls(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller]) as client:
        response = client.get("/schema/redoc")
        default_redoc_version = "next"
        default_redoc_js_bundle = (
            f"https://cdn.jsdelivr.net/npm/redoc@{default_redoc_version}/bundles/redoc.standalone.js"
        )
        assert client.app.openapi_config is not None
        assert client.app.openapi_config.openapi_controller.redoc_js_url == default_redoc_js_bundle
        assert default_redoc_js_bundle in response.text


def test_default_swagger_ui_cdn_urls(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller]) as client:
        response = client.get("/schema/swagger")
        default_swagger_bundles = [
            f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{OpenAPIController.swagger_ui_version}/swagger-ui.css",
            f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{OpenAPIController.swagger_ui_version}/swagger-ui-bundle.js",
            f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{OpenAPIController.swagger_ui_version}/swagger-ui-standalone-preset.js",
        ]
        assert client.app.openapi_config is not None
        assert client.app.openapi_config.openapi_controller.swagger_css_url in default_swagger_bundles
        assert client.app.openapi_config.openapi_controller.swagger_ui_bundle_js_url in default_swagger_bundles
        assert (
            client.app.openapi_config.openapi_controller.swagger_ui_standalone_preset_js_url in default_swagger_bundles
        )
        assert all(cdn_url in response.text for cdn_url in default_swagger_bundles)


def test_default_stoplight_elements_cdn_urls(
    person_controller: Type[Controller], pet_controller: Type[Controller]
) -> None:
    with create_test_client([person_controller, pet_controller]) as client:
        response = client.get("/schema/elements")
        default_stoplight_elements_bundles = [
            f"https://unpkg.com/@stoplight/elements@{OpenAPIController.stoplight_elements_version}/styles.min.css",
            f"https://unpkg.com/@stoplight/elements@{OpenAPIController.stoplight_elements_version}/web-components.min.js",
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


def test_default_rapidoc_cdn_urls(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller]) as client:
        response = client.get("/schema/rapidoc")
        default_rapidoc_bundles = [f"https://unpkg.com/rapidoc@{OpenAPIController.rapidoc_version}/dist/rapidoc-min.js"]
        assert client.app.openapi_config is not None
        assert client.app.openapi_config.openapi_controller.rapidoc_js_url in default_rapidoc_bundles
        assert all(cdn_url in response.text for cdn_url in default_rapidoc_bundles)


def test_redoc_with_google_fonts(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller]) as client:
        response = client.get("/schema/redoc")
        google_font_cdn = "https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700"
        assert client.app.openapi_config is not None
        assert client.app.openapi_config.openapi_controller.redoc_google_fonts is True
        assert google_font_cdn in response.text


def test_redoc_without_google_fonts(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    class OfflineOpenAPIController(OpenAPIController):
        """test class for usage in a couple "offline" tests and for without Google fonts test."""

        redoc_google_fonts = False

    offline_config = OpenAPIConfig(title="Litestar API", version="1.0.0", openapi_controller=OfflineOpenAPIController)
    with create_test_client([person_controller, pet_controller], openapi_config=offline_config) as client:
        response = client.get("/schema/redoc")
        assert "fonts.googleapis.com" not in response.text


def test_openapi_redoc_offline(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    class OfflineOpenAPIController(OpenAPIController):
        """test class for usage in a couple "offline" tests and for without Google fonts test."""

        redoc_js_url = "https://offline_location/redoc.standalone.js"

    offline_config = OpenAPIConfig(title="Litestar API", version="1.0.0", openapi_controller=OfflineOpenAPIController)
    with create_test_client([person_controller, pet_controller], openapi_config=offline_config) as client:
        response = client.get("/schema/redoc")
        assert OfflineOpenAPIController.redoc_js_url in response.text


def test_openapi_swagger_offline(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    class OfflineOpenAPIController(OpenAPIController):
        """test class for usage in a couple "offline" tests and for without Google fonts test."""

        swagger_css_url = "https://offline_location/swagger-ui-css"
        swagger_ui_bundle_js_url = "https://offline_location/swagger-ui-bundle.js"
        swagger_ui_standalone_preset_js_url = "https://offline_location/swagger-ui-standalone-preset.js"

    offline_config = OpenAPIConfig(title="Litestar API", version="1.0.0", openapi_controller=OfflineOpenAPIController)
    with create_test_client([person_controller, pet_controller], openapi_config=offline_config) as client:
        response = client.get("/schema/swagger")
        assert OfflineOpenAPIController.swagger_css_url in response.text
        assert OfflineOpenAPIController.swagger_ui_bundle_js_url in response.text
        assert OfflineOpenAPIController.swagger_ui_standalone_preset_js_url in response.text


def test_openapi_stoplight_elements_offline(
    person_controller: Type[Controller], pet_controller: Type[Controller]
) -> None:
    class OfflineOpenAPIController(OpenAPIController):
        """test class for usage in a couple "offline" tests and for without Google fonts test."""

        stoplight_elements_css_url = "https://offline_location/spotlight-styles.mins.css"
        stoplight_elements_js_url = "https://offline_location/spotlight-web-components.min.js"

    offline_config = OpenAPIConfig(title="Litestar API", version="1.0.0", openapi_controller=OfflineOpenAPIController)
    with create_test_client([person_controller, pet_controller], openapi_config=offline_config) as client:
        response = client.get("/schema/elements")
        assert OfflineOpenAPIController.stoplight_elements_css_url in response.text
        assert OfflineOpenAPIController.stoplight_elements_js_url in response.text


def test_openapi_rapidoc_offline(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    class OfflineOpenAPIController(OpenAPIController):
        """test class for usage in a couple "offline" tests and for without Google fonts test."""

        rapidoc_js_url = "https://offline_location/rapidoc-min.js"

    offline_config = OpenAPIConfig(title="Litestar API", version="1.0.0", openapi_controller=OfflineOpenAPIController)
    with create_test_client([person_controller, pet_controller], openapi_config=offline_config) as client:
        response = client.get("/schema/rapidoc")
        assert OfflineOpenAPIController.rapidoc_js_url in response.text


@pytest.mark.parametrize("root_path", root_paths)
def test_openapi_root(root_path: str, person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller], root_path=root_path) as client:
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


@pytest.mark.parametrize("root_path", root_paths)
def test_openapi_redoc(root_path: str, person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller], root_path=root_path) as client:
        response = client.get("/schema/redoc")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


@pytest.mark.parametrize("root_path", root_paths)
def test_openapi_swagger(root_path: str, person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller], root_path=root_path) as client:
        response = client.get("/schema/swagger")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


@pytest.mark.parametrize("root_path", root_paths)
def test_openapi_swagger_caching_schema(
    root_path: str, person_controller: Type[Controller], pet_controller: Type[Controller]
) -> None:
    with create_test_client([person_controller, pet_controller], root_path=root_path) as client:
        # Make sure that the schema is tweaked for swagger as the openapi version is changed.
        # Because schema can get cached, make sure that getting a different schema type before works.
        client.get("/schema/redoc")  # Cache the schema
        response = client.get("/schema/swagger")  # Request swagger, should use a different cache

        assert "3.1.0" in response.text  # Make sure the injected version is still there
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


@pytest.mark.parametrize("root_path", root_paths)
def test_openapi_stoplight_elements(
    root_path: str, person_controller: Type[Controller], pet_controller: Type[Controller]
) -> None:
    with create_test_client([person_controller, pet_controller], root_path=root_path) as client:
        response = client.get("/schema/elements/")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


@pytest.mark.parametrize("root_path", root_paths)
def test_openapi_rapidoc(root_path: str, person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client([person_controller, pet_controller], root_path=root_path) as client:
        response = client.get("/schema/rapidoc")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_root_not_allowed(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client(
        [person_controller, pet_controller],
        openapi_config=OpenAPIConfig(
            title="Litestar API",
            version="1.0.0",
            enabled_endpoints={"swagger", "elements", "openapi.json", "openapi.yaml", "openapi.yml"},
        ),
    ) as client:
        response = client.get("/schema")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_redoc_not_allowed(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client(
        [person_controller, pet_controller],
        openapi_config=OpenAPIConfig(
            title="Litestar API",
            version="1.0.0",
            enabled_endpoints={"swagger", "elements", "openapi.json", "openapi.yaml", "openapi.yml"},
        ),
    ) as client:
        response = client.get("/schema/redoc")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_swagger_not_allowed(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client(
        [person_controller, pet_controller],
        openapi_config=OpenAPIConfig(
            title="Litestar API",
            version="1.0.0",
            enabled_endpoints={"redoc", "elements", "openapi.json", "openapi.yaml", "openapi.yml"},
        ),
    ) as client:
        response = client.get("/schema/swagger")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_stoplight_elements_not_allowed(
    person_controller: Type[Controller], pet_controller: Type[Controller]
) -> None:
    with create_test_client(
        [person_controller, pet_controller],
        openapi_config=OpenAPIConfig(
            title="Litestar API",
            version="1.0.0",
            enabled_endpoints={"redoc", "swagger", "openapi.json", "openapi.yaml", "openapi.yml"},
        ),
    ) as client:
        response = client.get("/schema/elements/")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_rapidoc_not_allowed(person_controller: Type[Controller], pet_controller: Type[Controller]) -> None:
    with create_test_client(
        [person_controller, pet_controller],
        openapi_config=OpenAPIConfig(
            title="Litestar API",
            version="1.0.0",
            enabled_endpoints={"swagger", "elements", "openapi.json", "openapi.yaml", "openapi.yml"},
        ),
    ) as client:
        response = client.get("/schema/rapidoc")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)
