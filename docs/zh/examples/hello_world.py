# 你好世界示例
from litestar import Litestar, get

@get("/")
def hello_world() -> str:
    return "你好，世界！"

app = Litestar(route_handlers=[hello_world])
