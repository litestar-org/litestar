from typing import Any, Dict, List, Type
from unittest.mock import MagicMock

from pydantic import BaseConfig, BaseModel

from litestar import Controller, Litestar, post
from litestar._openapi.request_body import create_request_body
from litestar._openapi.schema_generation import SchemaCreator
from litestar.datastructures.upload_file import UploadFile
from litestar.dto import AbstractDTO
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.typing import FieldDefinition


class FormData(BaseModel):
    cv: UploadFile
    image: UploadFile

    class Config(BaseConfig):
        arbitrary_types_allowed = True


def test_create_request_body(person_controller: Type[Controller]) -> None:
    for route in Litestar(route_handlers=[person_controller]).routes:
        for route_handler, _ in route.route_handler_map.values():  # type: ignore
            handler_fields = route_handler.signature_model._fields
            if "data" in handler_fields:
                request_body = create_request_body(
                    route_handler=route_handler,
                    field_definition=handler_fields["data"],
                    schema_creator=SchemaCreator(generate_examples=True),
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


def test_request_body_generation_with_dto() -> None:
    mock_dto = MagicMock(spec=AbstractDTO)

    @post(path="/form-upload", dto=mock_dto)
    async def handler(data: Dict[str, Any]) -> None:
        return None

    Litestar(route_handlers=[handler])
    schema_creator = SchemaCreator()
    field_definition = FieldDefinition.from_annotation(Dict[str, Any])
    create_request_body(
        route_handler=handler,
        field_definition=field_definition,
        schema_creator=schema_creator,
    )

    mock_dto.create_openapi_schema.assert_called_once_with(
        field_definition=field_definition, handler_id=handler.handler_id, schema_creator=schema_creator
    )
