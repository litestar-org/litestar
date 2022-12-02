from typing import List, Dict
from starlite import Body, RequestEncodingType, UploadFile, post, Starlite


@post(path="/")
async def handle_file_upload(
    data: List[UploadFile] = Body(media_type=RequestEncodingType.MULTI_PART),
) -> Dict[str, str]:
    file_contents = {}
    for file in data:
        content = await file.read()
        file_contents[file.filename] = content.decode()

    return file_contents


app = Starlite(route_handlers=[handle_file_upload])
