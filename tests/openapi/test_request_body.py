from typing import List

from pydantic import BaseConfig, BaseModel

from starlite import Starlite, post
from starlite._openapi.request_body import create_request_body
from starlite.datastructures.upload_file import UploadFile
from starlite.enums import RequestEncodingType
from starlite.params import Body
from tests.openapi.utils import PersonController


class FormData(BaseModel):
    cv: UploadFile
    image: UploadFile

    class Config(BaseConfig):
        arbitrary_types_allowed = True


def test_create_request_body() -> None:
    for route in Starlite(route_handlers=[PersonController]).routes:
        for route_handler, _ in route.route_handler_map.values():  # type: ignore
            handler_fields = route_handler.signature_model.fields  # type: ignore
            if "data" in handler_fields:
                request_body = create_request_body(
                    field=handler_fields["data"], generate_examples=True, plugins=[], schemas={}
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

    app = Starlite(route_handlers=[handle_form_upload, handle_file_upload, handle_file_list_upload])
    schema_dict = app.openapi_schema.to_schema()
    paths = schema_dict["paths"]
    components = schema_dict["components"]
    assert paths["/file-upload"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"] == {
        "type": "string",
        "format": "binary",
        "contentMediaType": "application/octet-stream",
    }
    assert paths["/file-list-upload"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"] == {
        "items": {"type": "string", "format": "binary", "contentMediaType": "application/octet-stream"},
        "type": "array",
    }
    assert components == {
        "schemas": {
            "FormData": {
                "properties": {
                    "cv": {
                        "type": "string",
                        "format": "binary",
                        "contentMediaType": "application/octet-stream",
                    },
                    "image": {
                        "type": "string",
                        "format": "binary",
                        "contentMediaType": "application/octet-stream",
                    },
                },
                "type": "object",
                "required": ["cv", "image"],
                "title": "FormData",
            }
        }
    }
