from typing import Any, Dict, List, Union

from litestar import Litestar, post

TODO_LIST: List[Dict[str, Union[str, bool]]] = []


@post("/")
async def add_item(data: Dict[str, Any]) -> List[Dict[str, Union[str, bool]]]:
    TODO_LIST.append(data)
    return TODO_LIST


app = Litestar([add_item])
