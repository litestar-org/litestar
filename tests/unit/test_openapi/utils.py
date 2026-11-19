from enum import Enum, StrEnum
from typing import Any

from litestar import Litestar
from litestar.exceptions import HTTPException
from litestar.openapi import OpenAPIConfig
from litestar.types import ControllerRouterHandler


def build_document(
    *route_handlers: ControllerRouterHandler, app_kwargs: dict[str, Any] | None = None, **config: Any
) -> dict[str, Any]:
    openapi_config = OpenAPIConfig(title="test", version="1", **config)
    app = Litestar(route_handlers=route_handlers, openapi_config=openapi_config, **(app_kwargs or {}))
    return app.openapi_schema.to_schema()


def request_body_component(document: dict[str, Any], path: str) -> dict[str, Any]:
    reference = document["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    component: dict[str, Any] = document["components"]["schemas"][reference.rsplit("/", 1)[-1]]
    return component


class PetException(HTTPException):
    status_code = 406


class Gender(StrEnum):
    """Docstring description"""

    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    ANY = "A"


class LuckyNumber(int, Enum):
    TWO = 2
    SEVEN = 7
