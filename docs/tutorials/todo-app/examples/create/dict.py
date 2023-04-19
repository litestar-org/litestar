from typing import Dict, List, Union

from litestar import Litestar, post

TODO_LIST: List[Dict[str, Union[str, bool]]] = []


@post("/")
async def add_item(data: Dict) -> List[Dict[str, Union[str, bool]]]:
    TODO_LIST.append(data)
    return TODO_LIST


app = Litestar([add_item])
