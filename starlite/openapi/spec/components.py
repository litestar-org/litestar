from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from starlite.openapi.spec.base import BaseSchemaObject

__all__ = ("Components",)


if TYPE_CHECKING:
    from starlite.openapi.spec.callback import Callback
    from starlite.openapi.spec.example import Example
    from starlite.openapi.spec.header import OpenAPIHeader
    from starlite.openapi.spec.link import Link
    from starlite.openapi.spec.parameter import Parameter
    from starlite.openapi.spec.path_item import PathItem
    from starlite.openapi.spec.reference import Reference
    from starlite.openapi.spec.request_body import RequestBody
    from starlite.openapi.spec.response import OpenAPIResponse
    from starlite.openapi.spec.schema import Schema
    from starlite.openapi.spec.security_scheme import SecurityScheme


@dataclass
class Components(BaseSchemaObject):
    """Holds a set of reusable objects for different aspects of the OAS.

    All objects defined within the components object will have no effect
    on the API unless they are explicitly referenced from properties
    outside the components object.
    """

    schemas: dict[str, Schema] | None = None
    """An object to hold reusable [Schema
    Objects](https://spec.openapis.org/oas/v3.1.0#schemaObject)."""

    responses: dict[str, OpenAPIResponse | Reference] | None = None
    """An object to hold reusable [Response
    Objects](https://spec.openapis.org/oas/v3.1.0#responseObject)."""

    parameters: dict[str, Parameter | Reference] | None = None
    """An object to hold reusable [Parameter
    Objects](https://spec.openapis.org/oas/v3.1.0#parameterObject)."""

    examples: dict[str, Example | Reference] | None = None
    """An object to hold reusable [Example
    Objects](https://spec.openapis.org/oas/v3.1.0#exampleObject)."""

    request_bodies: dict[str, RequestBody | Reference] | None = None
    """An object to hold reusable [Request Body
    Objects](https://spec.openapis.org/oas/v3.1.0#requestBodyObject)."""

    headers: dict[str, OpenAPIHeader | Reference] | None = None
    """An object to hold reusable [Header
    Objects](https://spec.openapis.org/oas/v3.1.0#headerObject)."""

    security_schemes: dict[str, SecurityScheme | Reference] | None = None
    """An object to hold reusable [Security Scheme
    Objects](https://spec.openapis.org/oas/v3.1.0#securitySchemeObject)."""

    links: dict[str, Link | Reference] | None = None
    """An object to hold reusable [Link
    Objects](https://spec.openapis.org/oas/v3.1.0#linkObject)."""

    callbacks: dict[str, Callback | Reference] | None = None
    """An object to hold reusable [Callback
    Objects](https://spec.openapis.org/oas/v3.1.0#callbackObject)."""

    path_items: dict[str, PathItem | Reference] | None = None
    """An object to hold reusable [Path Item
    Object](https://spec.openapis.org/oas/v3.1.0#pathItemObject)."""
