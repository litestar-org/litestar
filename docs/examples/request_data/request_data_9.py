from typing import Dict

from starlite import Body, RequestEncodingType, Starlite, UploadFile, post


@post(path="/")
async def handle_file_upload(
    data: Dict[str, UploadFile] = Body(media_type=RequestEncodingType.MULTI_PART),
) -> Dict[str, str]:
    file_contents = {}
    for name, file in data.items():
        content = await file.read()
        file_contents[name] = content.decode()

    return file_contents


app = Starlite(route_handlers=[handle_file_upload])
