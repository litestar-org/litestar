from pydantic import BaseModel

from starlite import Body, RequestEncodingType, Starlite, post
from starlite.datastructures import UploadFile
from starlite.openapi.request_body import create_request_body
from tests.openapi.utils import PersonController


class FormData(BaseModel):
    cv: UploadFile
    image: UploadFile

    class Config:
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
