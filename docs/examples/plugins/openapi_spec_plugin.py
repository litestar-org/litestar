from typing import Any

from litestar import Litestar, get
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec import Components, SecurityRequirement, SecurityScheme
from litestar.plugins import OpenAPISpecPlugin


class BearerJWTSpecPlugin(OpenAPISpecPlugin):
    """Contribute a single ``BearerJWT`` security scheme and require it on every operation."""

    def get_openapi_components(self) -> Components:
        return Components(
            security_schemes={
                "BearerJWT": SecurityScheme(type="http", scheme="bearer", bearer_format="JWT"),
            },
        )

    def get_openapi_security_requirements(self, route_handler: Any) -> list[SecurityRequirement]:
        return [{"BearerJWT": []}]


@get("/items", sync_to_thread=False)
def list_items() -> list[str]:
    return []


app = Litestar(
    route_handlers=[list_items],
    plugins=[BearerJWTSpecPlugin()],
    openapi_config=OpenAPIConfig(title="My API", version="1.0.0"),
)
