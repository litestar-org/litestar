# 启动与关闭事件示例
from litestar import Litestar, on_startup, on_shutdown, get

@on_startup
async def startup() -> None:
    print("应用启动！")

@on_shutdown
async def shutdown() -> None:
    print("应用关闭！")

@get("/")
def index() -> str:
    return "应用已启动！"

app = Litestar(route_handlers=[index], on_startup=[startup], on_shutdown=[shutdown])
