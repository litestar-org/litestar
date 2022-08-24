from pydantic import BaseConfig, BaseModel

from starlite import Body, RequestEncodingType, Starlite, post
from starlite.datastructures import UploadFile
from starlite.openapi.request_body import create_request_body
from tests.openapi.utils import PersonController


class FormData(BaseModel):
    cv: UploadFile
    image: UploadFile

    class Config(BaseConfig):
        arbitrary_types_allowed = True


@post(path="/file-upload")
async def handle_file_upload(
    data: FormData = Body(media_type=RequestEncodingType.MULTI_PART),
) -> None:
    return None


def test_create_request_body() -> None:
    for route in Starlite(route_handlers=[PersonController, handle_file_upload]).routes:
        for route_handler, _ in route.route_handler_map.values():  # type: ignore
            handler_fields = route_handler.signature_model.__fields__
            if "data" in handler_fields:
                request_body = create_request_body(field=handler_fields["data"], generate_examples=True, plugins=[])
                assert request_body


def test_upload_file_request_body() -> None:
    app = Starlite(route_handlers=[handle_file_upload])
    assert app.openapi_schema.dict(exclude_none=True)["components"] == {  # type: ignore[union-attr]
        "schemas": {
            "FormData": {
                "properties": {
                    "cv": {
                        "properties": {"filename": {"type": "string", "contentMediaType": "application/octet-stream"}},
                        "type": "object",
                        "title": "Cv",
                    },
                    "image": {
                        "properties": {"filename": {"type": "string", "contentMediaType": "application/octet-stream"}},
                        "type": "object",
                        "title": "Image",
                    },
                },
                "type": "object",
                "required": ["cv", "image"],
                "title": "FormData",
            }
        }
    }
