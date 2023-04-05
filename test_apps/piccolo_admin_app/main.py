import asyncio
from typing import TYPE_CHECKING, List

from home.piccolo_app import APP_CONFIG
from home.tables import Task
from piccolo.apps.user.tables import BaseUser
from piccolo_admin.endpoints import create_admin  # pyright: ignore
from piccolo_api.session_auth.tables import SessionsBase

from starlite import Starlite, asgi, delete, get, patch, post
from starlite.contrib.piccolo_orm import PiccoloORMPlugin
from starlite.exceptions import NotFoundException

if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


@asgi("/admin/", is_mount=True)
async def admin(scope: "Scope", receive: "Receive", send: "Send") -> None:
    await create_admin(tables=APP_CONFIG.table_classes)(scope, receive, send)


@get("/tasks", tags=["Task"])
async def tasks() -> List[Task]:
    return await Task.select().order_by(Task.id, ascending=False)


@post("/tasks", tags=["Task"])
async def create_task(data: Task) -> Task:
    task = Task(**data.to_dict())
    await task.save()
    return task


@patch("/tasks/{task_id:int}", tags=["Task"])
async def update_task(task_id: int, data: Task) -> Task:
    task = await Task.objects().get(Task.id == task_id)
    if not task:
        raise NotFoundException("task does not exist")
    for key, value in data.to_dict().items():
        task.id = task_id
        setattr(task, key, value)

    await task.save()
    return task


@delete("/tasks/{task_id:int}", tags=["Task"])
async def delete_task(task_id: int) -> None:
    task = await Task.objects().get(Task.id == task_id)
    if task:
        await task.remove()


async def main():
    # Creating tables
    await BaseUser.create_table(if_not_exists=True)
    await SessionsBase.create_table(if_not_exists=True)
    await Task.create_table(if_not_exists=True)

    # Creating admin user
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


app = Starlite(
    route_handlers=[
        admin,
        tasks,
        create_task,
        update_task,
        delete_task,
    ],
    plugins=[PiccoloORMPlugin()],
)

if __name__ == "__main__":
    asyncio.run(main())

    import uvicorn

    uvicorn.run(app)
