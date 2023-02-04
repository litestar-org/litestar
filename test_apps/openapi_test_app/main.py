from typing import Dict

from starlite import Starlite, get
from starlite.exceptions import MissingDependencyException
from tests.openapi.utils import PersonController, PetController


@get("/")
async def greet() -> Dict[str, str]:
    return {"hello": "world"}


app = Starlite(
    route_handlers=[greet, PersonController, PetController],
)


if __name__ == "__main__":
    try:
        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=8000)
    except ImportError as e:
        raise MissingDependencyException("uvicorn is not installed") from e
