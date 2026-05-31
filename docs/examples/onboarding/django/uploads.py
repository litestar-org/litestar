from typing import Dict, List, Optional

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.params import MultipartBody


@post("/upload")
async def upload_files(data: MultipartBody[List[UploadFile]]) -> Dict[str, List[Optional[str]]]:
    return {"file_names": [file.filename for file in data]}


app = Litestar(route_handlers=[upload_files])
