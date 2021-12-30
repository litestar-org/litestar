from typing import cast

import yaml
from openapi_schema_pydantic import OpenAPI
from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from orjson import loads
from starlette.status import HTTP_200_OK

from starlite import OpenAPIController, Starlite, create_test_client, get
from starlite.config import OpenAPIConfig
from starlite.enums import OpenAPIMediaType
from starlite.request import Request
from tests.openapi.utils import PersonController, PetController


class OpenAPIControllerWithYaml(OpenAPIController):
    @get(media_type=OpenAPIMediaType.OPENAPI_YAML, include_in_schema=False)
    def retrieve_schema(self, request: Request) -> OpenAPI:
        return self.schema_from_request(request)


def test_openapi_yaml():
    with create_test_client(
        [PersonController, PetController, OpenAPIControllerWithYaml],
        openapi_config=OpenAPIConfig(title="starlite", version="1"),
    ) as client:
        app = cast(Starlite, client.app)
        assert app.openapi_schema
        openapi_schema = app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_YAML.value
        assert yaml.safe_load(response.content) == construct_open_api_with_schema_class(app.openapi_schema).dict(
            by_alias=True, exclude_none=True
        )


def test_openapi_json():
    with create_test_client(
        [PersonController, PetController, OpenAPIController],
        openapi_config=OpenAPIConfig(title="starlite", version="1"),
    ) as client:
        app = cast(Starlite, client.app)
        assert app.openapi_schema
        openapi_schema = app.openapi_schema
        assert openapi_schema.paths
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == OpenAPIMediaType.OPENAPI_JSON.value
        assert response.json() == loads(
            construct_open_api_with_schema_class(app.openapi_schema).json(by_alias=True, exclude_none=True)
        )
