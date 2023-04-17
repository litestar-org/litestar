from dataclasses import dataclass
from typing import List

from litestar import Litestar, put
from litestar.exceptions import NotFoundException


@dataclass
class TodoItem:
    title: str
    done: bool


TODO_LIST = []


def get_todo_by_title(todo_name) -> TodoItem:
    for item in TODO_LIST:
        if item.name == todo_name:
            return item
    raise NotFoundException(detail=f"TODO {todo_name!r} not found")


@put("/{item_title:str}")
async def add_item(item_title: str, data: TodoItem) -> List[TodoItem]:
    todo_item = get_todo_by_title(item_title)
    todo_item.title = data.title
    todo_item.done = data.done
    return TODO_LIST


app = Litestar([add_item])
