from dataclasses import dataclass
from typing import Any, Dict, List, Type
from unittest.mock import MagicMock

import pytest

from litestar import Controller, Litestar, post
from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.request_body import RequestBodyFactory
from litestar.datastructures.upload_file import UploadFile
from litestar.dto import AbstractDTO
from litestar.enums import RequestEncodingType
from litestar.openapi.config import OpenAPIConfig
from litestar.params import Body
from litestar.typing import FieldDefinition


@dataclass
class FormData:
    cv: UploadFile
    image: UploadFile


@pytest.fixture()
def factory() -> RequestBodyFactory:
    return RequestBodyFactory(
        context=OpenAPIContext(
            openapi_config=OpenAPIConfig(title="test", version="1.0.0", create_examples=True),
            plugins=[],
            schemas={},
        )
    )


def test_create_request_body(person_controller: Type[Controller], factory: RequestBodyFactory) -> None:
    for route in Litestar(route_handlers=[person_controller]).routes:
        for route_handler, _ in route.route_handler_map.values():  # type: ignore
            handler_fields = route_handler.signature_model._fields
            if "data" in handler_fields:
                request_body = factory.create_request_body(
                    route_handler=route_handler,
                    field_definition=handler_fields["data"],
                )
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
            "tests_unit_test_openapi_test_request_body_FormData": {
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


def test_request_body_generation_with_dto(factory: RequestBodyFactory) -> None:
    mock_dto = MagicMock(spec=AbstractDTO)

    @post(path="/form-upload", dto=mock_dto)  # pyright: ignore
    async def handler(data: Dict[str, Any]) -> None:
        return None

    Litestar(route_handlers=[handler])
    field_definition = FieldDefinition.from_annotation(Dict[str, Any])
    factory.create_request_body(
        route_handler=handler,
        field_definition=field_definition,
    )

    mock_dto.create_openapi_schema.assert_called_once_with(
        field_definition=field_definition, handler_id=handler.handler_id, schema_creator=factory.schema_creator
    )
