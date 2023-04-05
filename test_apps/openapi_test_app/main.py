from typing import Dict

from starlite import Starlite, get
from tests.openapi.utils import PersonController, PetController


@get("/")
async def greet() -> Dict[str, str]:
    return {"hello": "world"}


app = Starlite(
    route_handlers=[greet, PersonController, PetController],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
