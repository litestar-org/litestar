from starlite import MediaType, Starlite, post
from starlite.datastructures import UploadFile
from starlite.enums import RequestEncodingType
from starlite.params import Body


@post(path="/", media_type=MediaType.TEXT)
async def handle_file_upload(
    data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART),
) -> str:
    content = await data.read()
    filename = data.filename
    return f"{filename}, {content.decode()}"


app = Starlite(route_handlers=[handle_file_upload])
