from dataclasses import dataclass
from typing import Dict

from typing import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.params import MultipartBody


@dataclass
class User:
    id: int
    name: str
    form_input_name: UploadFile


@post(path="/")
async def create_user(data: MultipartBody[User]) -> dict[str, str]:
    content = await data.form_input_name.read()
    filename = data.form_input_name.filename
    return {"id": data.id, "name": data.name, "filename": filename, "size": len(content)}


app = Litestar(route_handlers=[create_user])
