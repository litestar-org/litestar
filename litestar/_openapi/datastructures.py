from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar.openapi import OpenAPIConfig
    from litestar.openapi.spec import Schema
    from litestar.plugins import OpenAPISchemaPluginProtocol


class OpenAPIContext:
    """OpenAPI Context.

    Context object used to support OpenAPI schema generation.
    """

    __slots__ = ("openapi_config", "plugins", "schemas", "operation_ids")

    def __init__(
        self, openapi_config: OpenAPIConfig, plugins: Sequence[OpenAPISchemaPluginProtocol], schemas: dict[str, Schema]
    ) -> None:
        """Initialize OpenAPIContext.

        Args:
            openapi_config: OpenAPIConfig instance.
            plugins: OpenAPI plugins.
            schemas: Mapping of schema names to schema objects that will become the components.schemas section of the
                OpenAPI schema.
        """
        self.openapi_config = openapi_config
        self.plugins = plugins
        self.schemas = schemas
        # used to track that operation ids are globally unique across the OpenAPI document
        self.operation_ids: set[str] = set()

    def add_operation_id(self, operation_id: str) -> None:
        """Add an operation ID to the context.

        Args:
            operation_id: Operation ID to add.
        """
        if operation_id in self.operation_ids:
            raise ImproperlyConfiguredException(
                f"operation_ids must be unique, "
                f"please ensure the value of 'operation_id' is either not set or unique for {operation_id}"
            )
        self.operation_ids.add(operation_id)
