from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar.openapi import OpenAPIConfig
    from litestar.openapi.spec import Reference, Schema
    from litestar.plugins import OpenAPISchemaPluginProtocol


class RegisteredSchema:
    def __init__(self, schema: Schema, references: list[Reference], current_schema_key: str) -> None:
        self.schema = schema
        self.references = references
        self.current_schema_key = current_schema_key


class SchemaRegistry:
    def __init__(self) -> None:
        self._schema_map: dict = {}

    def register(
        self,
        key: tuple[str, ...],
        schema: Schema,
        reference: Reference,
        current_schema_key: str,
    ) -> None:
        if (registered_schema := self._schema_map.get(key)) is not None:
            registered_schema.references.append(reference)
            return

        self._schema_map[key] = RegisteredSchema(schema, [reference], current_schema_key)


class OpenAPIContext:
    def __init__(
        self, openapi_config: OpenAPIConfig, plugins: Sequence[OpenAPISchemaPluginProtocol], schemas: dict[str, Schema]
    ) -> None:
        self.openapi_config = openapi_config
        self.plugins = plugins
        self.schemas = schemas
        self.operation_ids: set[str] = set()
        self.schema_registry = SchemaRegistry()

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
