from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Type
from unittest.mock import ANY, MagicMock

import pytest

from litestar import Controller, Litestar, post
from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.request_body import create_request_body
from litestar.datastructures.upload_file import UploadFile
from litestar.dto import AbstractDTO
from litestar.enums import RequestEncodingType
from litestar.handlers import BaseRouteHandler
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import RequestBody
from litestar.params import Body
from litestar.typing import FieldDefinition


@dataclass
class FormData:
    cv: UploadFile
    image: UploadFile


RequestBodyFactory = Callable[[BaseRouteHandler, FieldDefinition], RequestBody]


@pytest.fixture()
def openapi_context() -> OpenAPIContext:
    return OpenAPIContext(
        openapi_config=OpenAPIConfig(title="test", version="1.0.0", create_examples=True),
        plugins=[],
    )


@pytest.fixture()
def create_request(openapi_context: OpenAPIContext) -> RequestBodyFactory:
    def _factory(route_handler: BaseRouteHandler, data_field: FieldDefinition) -> RequestBody:
        return create_request_body(
            context=openapi_context,
            handler_id=route_handler.handler_id,
            resolved_data_dto=route_handler.resolve_data_dto(),
            data_field=data_field,
        )

    return _factory


def test_create_request_body(person_controller: Type[Controller], create_request: RequestBodyFactory) -> None:
    for route in Litestar(route_handlers=[person_controller]).routes:
        for route_handler, _ in route.route_handler_map.values():  # type: ignore
            handler_fields = route_handler.parsed_fn_signature.parameters
            if "data" in handler_fields:
                request_body = create_request(route_handler, handler_fields["data"])
                assert request_body


def test_upload_file_request_body_generation() -> None:
    @post(path="/form-upload")
    async def handle_form_upload(
        data: FormData = Body(media_type=RequestEncodingType.MULTI_PART),
    ) -> None:
        return None

    @post(path="/file-upload")
    async def handle_file_upload(
        data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART),
    ) -> None:
        return None

    @post(path="/file-list-upload")
    async def handle_file_list_upload(
        data: List[UploadFile] = Body(media_type=RequestEncodingType.MULTI_PART),
    ) -> None:
        return None

    app = Litestar(route_handlers=[handle_form_upload, handle_file_upload, handle_file_list_upload])
    schema_dict = app.openapi_schema.to_schema()
    paths = schema_dict["paths"]
    components = schema_dict["components"]
    assert paths["/file-upload"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"] == {
        "type": "string",
        "contentMediaType": "application/octet-stream",
    }
    assert paths["/file-list-upload"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"] == {
        "items": {"type": "string", "contentMediaType": "application/octet-stream"},
        "type": "array",
    }

    assert components == {
        "schemas": {
            "FormData": {
                "properties": {
                    "cv": {
                        "type": "string",
                        "contentMediaType": "application/octet-stream",
                    },
                    "image": {
                        "type": "string",
                        "contentMediaType": "application/octet-stream",
                    },
                },
                "type": "object",
                "required": ["cv", "image"],
                "title": "FormData",
            }
        }
    }


def test_request_body_generation_with_dto(create_request: RequestBodyFactory) -> None:
    mock_dto = MagicMock(spec=AbstractDTO)

    @post(path="/form-upload", dto=mock_dto)  # pyright: ignore
    async def handler(data: Dict[str, Any]) -> None:
        return None

    Litestar(route_handlers=[handler])
    field_definition = FieldDefinition.from_annotation(Dict[str, Any])
    create_request(handler, field_definition)
    mock_dto.create_openapi_schema.assert_called_once_with(
        field_definition=field_definition, handler_id=handler.handler_id, schema_creator=ANY
    )
