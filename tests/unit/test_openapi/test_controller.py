from typing import List, Type

import pytest

from litestar import Controller
from litestar.enums import MediaType
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.controller import OpenAPIController
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client

root_paths: List[str] = ["", "/part1", "/part1/part2"]


class OfflineOpenAPIControllerRedoc(OpenAPIController):
    redoc_js_url = "https://offline_location/redoc.standalone.js"
    redoc_google_fonts = False


class OfflineOpenAPIControllerSwagger(OpenAPIController):
    swagger_css_url = "https://offline_location/swagger-ui-css"
    swagger_ui_bundle_js_url = "https://offline_location/swagger-ui-bundle.js"
    swagger_ui_standalone_preset_js_url = "https://offline_location/swagger-ui-standalone-preset.js"


class OfflineOpenAPIControllerStoplight(OpenAPIController):
    stoplight_elements_css_url = "https://offline_location/spotlight-styles.mins.css"
    stoplight_elements_js_url = "https://offline_location/spotlight-web-components.min.js"


class OfflineOpenAPIControllerRapidoc(OpenAPIController):
    rapidoc_js_url = "https://offline_location/rapidoc-min.js"


class OfflineOpenAPIControllerScalar(OpenAPIController):
    scalar_js_url = "https://offline_location/scalar-min.js"


@pytest.mark.parametrize(
    "endpoint, version, cdn_urls",
    [
        (
            "/schema/swagger",
            OpenAPIController.swagger_ui_version,
            [
                "https://cdn.jsdelivr.net/npm/swagger-ui-dist@{}/swagger-ui.css",
                "https://cdn.jsdelivr.net/npm/swagger-ui-dist@{}/swagger-ui-bundle.js",
                "https://cdn.jsdelivr.net/npm/swagger-ui-dist@{}/swagger-ui-standalone-preset.js",
            ],
        ),
        (
            "/schema/elements",
            OpenAPIController.stoplight_elements_version,
            [
                "https://unpkg.com/@stoplight/elements@{}/styles.min.css",
                "https://unpkg.com/@stoplight/elements@{}/web-components.min.js",
            ],
        ),
        ("/schema/redoc", "next", ["https://cdn.jsdelivr.net/npm/redoc@{}/bundles/redoc.standalone.js"]),
        ("/schema/rapidoc", OpenAPIController.rapidoc_version, ["https://unpkg.com/rapidoc@{}/dist/rapidoc-min.js"]),
        ("/schema/scalar", OpenAPIController.scalar_version, ["https://cdn.jsdelivr.net/npm/@scalar/api-reference@{}"]),
    ],
)
def test_default_cdn_urls(
    endpoint: str,
    version: str,
    cdn_urls: List[str],
    person_controller: Type[Controller],
    pet_controller: Type[Controller],
) -> None:
    with create_test_client([person_controller, pet_controller]) as client:
        response = client.get(endpoint)
        formatted_cdn_urls = [url.format(version) for url in cdn_urls]
        assert client.app.openapi_config is not None
        assert all(url in response.text for url in formatted_cdn_urls)


@pytest.mark.parametrize(
    "openapi_controller, should_have_google_fonts", [(OpenAPIController, True), (OfflineOpenAPIControllerRedoc, False)]
)
def test_redoc_google_fonts(
    person_controller: Type[Controller],
    pet_controller: Type[Controller],
    openapi_controller: Type[OpenAPIController],
    should_have_google_fonts: bool,
) -> None:
    google_font_cdn = "https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700"
    config = OpenAPIConfig(title="Litestar API", version="1.0.0", openapi_controller=openapi_controller)

    with create_test_client([person_controller, pet_controller], openapi_config=config) as client:
        response = client.get("/schema/redoc")
        if should_have_google_fonts:
            assert google_font_cdn in response.text
        else:
            assert google_font_cdn not in response.text


@pytest.mark.parametrize(
    "endpoint, controller_class, urls_to_check",
    [
        (
            "/schema/swagger",
            OfflineOpenAPIControllerSwagger,
            [
                OfflineOpenAPIControllerSwagger.swagger_css_url,
                OfflineOpenAPIControllerSwagger.swagger_ui_bundle_js_url,
                OfflineOpenAPIControllerSwagger.swagger_ui_standalone_preset_js_url,
            ],
        ),
        (
            "/schema/elements",
            OfflineOpenAPIControllerStoplight,
            [
                OfflineOpenAPIControllerStoplight.stoplight_elements_css_url,
                OfflineOpenAPIControllerStoplight.stoplight_elements_js_url,
            ],
        ),
        ("/schema/redoc", OfflineOpenAPIControllerRedoc, [OfflineOpenAPIControllerRedoc.redoc_js_url]),
        ("/schema/rapidoc", OfflineOpenAPIControllerRapidoc, [OfflineOpenAPIControllerRapidoc.rapidoc_js_url]),
        ("/schema/scalar", OfflineOpenAPIControllerScalar, [OfflineOpenAPIControllerScalar.scalar_js_url]),
    ],
)
def test_openapi_endpoints_offline(
    endpoint: str,
    controller_class: Type[OpenAPIController],
    urls_to_check: List[str],
    person_controller: Type[Controller],
    pet_controller: Type[Controller],
) -> None:
    offline_config = OpenAPIConfig(title="Litestar API", version="1.0.0", openapi_controller=controller_class)
    with create_test_client([person_controller, pet_controller], openapi_config=offline_config) as client:
        response = client.get(endpoint)
        for url in urls_to_check:
            assert url in response.text


@pytest.mark.parametrize(
    "root_path, endpoint",
    [(root_path, "/schema") for root_path in root_paths]
    + [(root_path, "/schema/redoc") for root_path in root_paths]
    + [(root_path, "/schema/swagger") for root_path in root_paths]
    + [(root_path, "/schema/elements/") for root_path in root_paths]
    + [(root_path, "/schema/rapidoc") for root_path in root_paths]
    + [(root_path, "/schema/scalar") for root_path in root_paths],
)
def test_openapi_endpoints(
    root_path: str, endpoint: str, person_controller: Type[Controller], pet_controller: Type[Controller]
) -> None:
    with create_test_client([person_controller, pet_controller], root_path=root_path) as client:
        response = client.get(endpoint)
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


@pytest.mark.parametrize(
    "endpoint",
    [
        "/schema",
        "/schema/redoc",
        "/schema/swagger",
        "/schema/elements/",
        "/schema/rapidoc",
        "/schema/scalar",
    ],
)
def test_openapi_endpoints_not_allowed(
    endpoint: str, person_controller: Type[Controller], pet_controller: Type[Controller]
) -> None:
    with create_test_client(
        [person_controller, pet_controller],
        openapi_config=OpenAPIConfig(
            title="Litestar API",
            version="1.0.0",
            enabled_endpoints={"openapi.json", "openapi.yaml", "openapi.yml"},
        ),
    ) as client:
        response = client.get(endpoint)
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)
