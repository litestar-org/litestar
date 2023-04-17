from typing import Dict, List, Union

from litestar import Litestar, post

TODO_LIST = []


@post("/")
async def add_item(data: Dict[str, Union[str, bool]]) -> List[Dict[str, Union[str, bool]]]:
    TODO_LIST.append(data)
    return TODO_LIST


app = Litestar([add_item])
