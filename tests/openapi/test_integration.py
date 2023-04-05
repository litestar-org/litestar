import yaml

from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.enums import OpenAPIMediaType
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client
from tests.openapi.utils import PersonController, PetController


def test_openapi_yaml() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.yaml")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_YAML.value
        assert client.app.openapi_schema
        assert yaml.unsafe_load(response.content) == client.app.openapi_schema.to_schema()


def test_openapi_json() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_JSON.value
        assert client.app.openapi_schema
        assert response.json() == client.app.openapi_schema.to_schema()


def test_openapi_yaml_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard("openapi.yaml")

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.yaml")
        assert response.status_code == HTTP_404_NOT_FOUND


def test_openapi_json_not_allowed() -> None:
    openapi_config = DEFAULT_OPENAPI_CONFIG
    openapi_config.enabled_endpoints.discard("openapi.json")

    with create_test_client([PersonController, PetController], openapi_config=openapi_config) as client:
        assert client.app.openapi_schema
        openapi_schema = client.app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_404_NOT_FOUND
