from typing import TYPE_CHECKING, List

from home.piccolo_app import APP_CONFIG
from home.tables import Task
from piccolo.engine import engine_finder

from starlite import (
    MissingDependencyException,
    NotFoundException,
    Starlite,
    StaticFilesConfig,
    TemplateConfig,
    asgi,
    delete,
    get,
    patch,
    post,
)
from starlite.plugins.piccolo_orm import PiccoloORMPlugin
from starlite.template.jinja import JinjaTemplateEngine

try:
    from piccolo_admin.endpoints import create_admin
except ImportError as e:
    raise MissingDependencyException("piccolo_admin is not installed") from e


if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


@asgi("/admin", is_mount=True)
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


async def open_database_connection_pool():
    engine = engine_finder()
    await engine.start_connection_pool()


async def close_database_connection_pool():
    engine = engine_finder()
    await engine.close_connection_pool()


app = Starlite(
    route_handlers=[
        admin,
        tasks,
        create_task,
        update_task,
        delete_task,
    ],
    plugins=[PiccoloORMPlugin()],
    template_config=TemplateConfig(directory="test_apps/piccolo_admin_app/home/templates", engine=JinjaTemplateEngine),
    static_files_config=[
        StaticFilesConfig(directories=["static"], path="/static/"),
    ],
    on_startup=[open_database_connection_pool],
    on_shutdown=[close_database_connection_pool],
)

if __name__ == "__main__":
    try:
        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=8000)
    except ImportError as e:
        raise MissingDependencyException("uvicorn is not installed") from e
