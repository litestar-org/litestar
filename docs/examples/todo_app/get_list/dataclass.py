from dataclasses import dataclass
from typing import List

from litestar import Litestar, get


@dataclass
class TodoItem:
    title: str
    done: bool


TODO_LIST: List[TodoItem] = [
    TodoItem(title="Start writing TODO list", done=True),
    TodoItem(title="???", done=False),
    TodoItem(title="Profit", done=False),
]


@get("/")
async def get_list() -> List[TodoItem]:
    return TODO_LIST


app = Litestar([get_list])
