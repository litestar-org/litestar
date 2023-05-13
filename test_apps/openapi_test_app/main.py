from typing import Dict

from litestar import Litestar, get
from tests.openapi.conftest import create_person_controller, create_pet_controller


@get("/")
async def greet() -> Dict[str, str]:
    return {"hello": "world"}


app = Litestar(
    route_handlers=[greet, create_person_controller(), create_pet_controller()],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
