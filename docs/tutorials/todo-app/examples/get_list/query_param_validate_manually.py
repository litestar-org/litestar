from dataclasses import dataclass
from typing import List

from litestar import Litestar, get
from litestar.exceptions import HTTPException


@dataclass
class TodoItem:
    title: str
    done: bool


TODO_LIST = [
    TodoItem(title="Start writing TODO list", done=True),
    TodoItem(title="???", done=False),
    TodoItem(title="Profit", done=False),
]


@get("/")
async def get_todo_list(done: str) -> List[TodoItem]:
    if done == "true":
        return [item for item in TODO_LIST if item.done]
    if done == "false":
        return [item for item in TODO_LIST if not item.done]
    raise HTTPException(f"Invalid query parameter value: {done!r}", status_code=400)


app = Litestar([get_todo_list])
