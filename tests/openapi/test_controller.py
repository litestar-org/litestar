import pytest
from starlette.status import HTTP_200_OK

from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.enums import MediaType
from starlite.testing import create_test_client
from tests.openapi.utils import PersonController, PetController


@pytest.mark.parametrize("url", ["/schema", "/schema/redoc"])
def test_openapi_redoc(url: str) -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get(url)
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)


def test_openapi_swagger() -> None:
    with create_test_client([PersonController, PetController], openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        response = client.get("/schema/swagger")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(MediaType.HTML.value)
