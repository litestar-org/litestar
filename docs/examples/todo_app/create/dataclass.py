from dataclasses import dataclass

from litestar import Litestar, post
from litestar.params import JSONBody


@dataclass
class TodoItem:
    title: str
    done: bool


TODO_LIST: list[TodoItem] = []


@post("/")
async def add_item(data: JSONBody[TodoItem]) -> list[TodoItem]:
    TODO_LIST.append(data)
    return TODO_LIST


app = Litestar([add_item])
