from dataclasses import dataclass
from typing import List

from litestar import Litestar, post


@dataclass
class TodoItem:
    title: str
    done: bool


TODO_LIST: List[TodoItem] = []


@post("/")
async def add_item(data: TodoItem) -> List[TodoItem]:
    TODO_LIST.append(data)
    return TODO_LIST


app = Litestar([add_item])
