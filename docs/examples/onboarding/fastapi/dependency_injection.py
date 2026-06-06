from litestar import Litestar, Router, get
from litestar.di import NamedDependency


async def route_dependency() -> bool:
    return True


async def nested_dependency() -> str:
    return "nested"


async def router_dependency() -> int:
    return 1


async def app_dependency(val_nested: NamedDependency[str]) -> int:
    return len(val_nested)


@get("/", dependencies={"val_route": route_dependency})
async def handler(
    val_route: NamedDependency[bool],
    val_router: NamedDependency[int],
    val_nested: NamedDependency[str],
    val_app: NamedDependency[int],
) -> dict[str, object]:
    return {
        "val_route": val_route,
        "val_router": val_router,
        "val_nested": val_nested,
        "val_app": val_app,
    }


router = Router(
    path="/",
    route_handlers=[handler],
    dependencies={"val_router": router_dependency},
)

app = Litestar(
    route_handlers=[router],
    dependencies={
        "val_app": app_dependency,
        "val_nested": nested_dependency,
    },
)
