from typing import cast

import yaml
from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from orjson import loads
from starlette.status import HTTP_200_OK

from starlite import Starlite, create_test_client
from starlite.config import OpenAPIConfig
from starlite.enums import OpenAPIMediaType
from tests.openapi.utils import PersonController, PetController


def test_openapi_yaml():
    with create_test_client([PersonController, PetController], openapi_config=OpenAPIConfig()) as client:
        app = cast(Starlite, client.app)
        assert app.router.openapi_schema
        openapi_schema = app.router.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_YAML.value
        assert yaml.safe_load(response.content) == construct_open_api_with_schema_class(app.router.openapi_schema).dict(
            by_alias=True, exclude_none=True
        )


def test_openapi_json():
    with create_test_client(
        [PersonController, PetController],
        openapi_config=OpenAPIConfig(schema_response_media_type=OpenAPIMediaType.OPENAPI_JSON),
    ) as client:
        app = cast(Starlite, client.app)
        assert app.router.openapi_schema
        openapi_schema = app.router.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_JSON.value
        assert response.json() == loads(
            construct_open_api_with_schema_class(app.router.openapi_schema).json(by_alias=True, exclude_none=True)
        )
