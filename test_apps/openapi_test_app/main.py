from typing import Dict

from litestar import Litestar, get
from litestar.openapi.config import OpenAPIConfig
from tests.unit.test_openapi.conftest import create_person_controller, create_pet_controller


@get("/")
async def greet() -> Dict[str, str]:
    return {"hello": "world"}


app = Litestar(
    route_handlers=[greet, create_person_controller(), create_pet_controller()],
    openapi_config=OpenAPIConfig(
        title="whatever",
        version="0.0.1",
        root_schema_site="rapidoc",
    ),
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
