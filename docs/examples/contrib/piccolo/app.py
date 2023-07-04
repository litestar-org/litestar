import asyncio
import typing as t

import uvicorn
from piccolo.apps.user.tables import BaseUser
from piccolo.columns import Boolean, Varchar
from piccolo.table import Table, create_db_tables
from piccolo_admin.endpoints import create_admin
from piccolo_api.session_auth.tables import SessionsBase

from litestar import Litestar, MediaType, asgi, delete, get, patch, post
from litestar.contrib.piccolo.dto import PiccoloDTO
from litestar.dto.factory import DTOConfig, DTOData
from litestar.exceptions import NotFoundException
from litestar.types import Receive, Scope, Send

from .piccolo_conf import DB


class Task(Table, db=DB):
    """
    An example table.
    """

    name = Varchar()
    completed = Boolean(default=False)


# mounting Piccolo Admin
@asgi("/admin/", is_mount=True)
async def admin(scope: "Scope", receive: "Receive", send: "Send") -> None:
    await create_admin(tables=[Task])(scope, receive, send)


class PatchDTO(PiccoloDTO[Task]):
    """Don't allow client to set the id, and allow partial updates."""

    config = DTOConfig(exclude={"id"}, partial=True)


@get(
    "/tasks",
    return_dto=PiccoloDTO[Task],
    media_type=MediaType.JSON,
    tags=["Task"],
)
async def tasks() -> t.List[Task]:
    return await Task.select().order_by(Task.id, ascending=False)


@post(
    "/tasks",
    dto=PiccoloDTO[Task],
    return_dto=PiccoloDTO[Task],
    media_type=MediaType.JSON,
    tags=["Task"],
)
async def create_task(data: Task) -> Task:
    await data.save()
    await data.refresh()
    return data


@patch(
    "/tasks/{task_id:int}",
    dto=PatchDTO,
    return_dto=PiccoloDTO[Task],
    media_type=MediaType.JSON,
    tags=["Task"],
)
async def update_task(task_id: int, data: DTOData[Task]) -> Task:
    task = await Task.objects().get(Task.id == task_id)
    if not task:
        raise NotFoundException("Task does not exist")
    result = data.update_instance(task)
    await result.save()
    return result


@delete("/tasks/{task_id:int}", tags=["Task"])
async def delete_task(task_id: int) -> None:
    task = await Task.objects().get(Task.id == task_id)
    if not task:
        raise NotFoundException("Task does not exist")
    await task.remove()


async def main():
    # Tables creating
    await create_db_tables(BaseUser, SessionsBase, Task, if_not_exists=True)

    # Creating admin users
    if not await BaseUser.exists().where(BaseUser.email == "admin@test.com"):
        user = BaseUser(
            username="piccolo",
            password="piccolo123",
            email="admin@test.com",
            admin=True,
            active=True,
            superuser=True,
        )
        await user.save()


app = Litestar(
    route_handlers=[
        admin,
        tasks,
        create_task,
        delete_task,
        update_task,
    ],
)

if __name__ == "__main__":
    asyncio.run(main())

    uvicorn.run(app, host="127.0.0.1", port=8000)
