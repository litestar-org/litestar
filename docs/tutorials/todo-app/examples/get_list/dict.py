from typing import Dict, List, Union

from litestar import Litestar, get

TODO_LIST: List[Dict[str, Union[str, bool]]] = [
    {"title": "Start writing TODO list", "done": True},
    {"title": "???", "done": False},
    {"title": "Profit", "done": False},
]


@get("/")
async def get_list() -> List[Dict[str, Union[str, bool]]]:
    return TODO_LIST


app = Litestar([get_list])
