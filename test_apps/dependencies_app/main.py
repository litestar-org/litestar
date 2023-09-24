from litestar import Litestar
from litestar import get
from litestar.di import Provide


def get_dependency() -> str:
    return "db"


dependencies = {"db": Provide(get_dependency)}


@get("/")
def my_handler(db: dict) -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(
    route_handlers=[my_handler],
    dependencies=dependencies,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
