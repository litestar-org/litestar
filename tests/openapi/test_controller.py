from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.enums import MediaType
from starlite.testing import create_test_client
from tests.openapi.utils import PersonController, PetController


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
    openapi_config.exposed_endpoints.discard(DEFAULT_OPENAPI_CONFIG.root_schema_site)

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        response = client.get("/schema")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_redoc_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.exposed_endpoints.discard("redoc")

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        response = client.get("/schema/redoc")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_swagger_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.exposed_endpoints.discard("swagger")

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        response = client.get("/schema/swagger")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_stoplight_elements_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.exposed_endpoints.discard("elements")

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        response = client.get("/schema/elements/")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.headers["content-type"].startswith(MediaType.HTML.value)
