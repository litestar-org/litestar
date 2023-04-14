from typing import Dict, List, Union

from litestar import Litestar, get

__all__ = ["get_todo_list"]


TODO_LIST = [
    {"title": "Start writing TODO list", "done": True},
    {"title": "???", "done": False},
    {"title": "Profit", "done": False},
]


@get("/")
async def get_todo_list() -> List[Dict[str, Union[str, bool]]]:
    return TODO_LIST


app = Litestar([get_todo_list])
