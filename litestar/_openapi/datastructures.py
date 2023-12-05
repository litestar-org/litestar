from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Iterator, Sequence

from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar.openapi import OpenAPIConfig
    from litestar.openapi.spec import Reference, Schema
    from litestar.plugins import OpenAPISchemaPluginProtocol


class RegisteredSchema:
    def __init__(self, key: tuple[str, ...], schema: Schema, references: list[Reference]) -> None:
        self.key = key
        self.schema = schema
        self.references = references

    def __repr__(self) -> str:
        return f"<RegisteredSchema key={self.key}>"


class SchemaRegistry:
    def __init__(self) -> None:
        self._schema_key_map: dict[tuple[str, ...], RegisteredSchema] = {}
        self._schema_reference_map: dict[int, RegisteredSchema] = {}
        self._model_name_groups: defaultdict[str, list[RegisteredSchema]] = defaultdict(list)

    def register(
        self,
        key: tuple[str, ...],
        schema: Schema,
        reference: Reference,
    ) -> None:
        if (registered_schema := self._schema_key_map.get(key)) is not None:
            registered_schema.references.append(reference)
            self._schema_reference_map[id(reference)] = registered_schema
            return

        self._schema_key_map[key] = registered_schema = RegisteredSchema(key, schema, [reference])
        self._schema_reference_map[id(reference)] = registered_schema
        self._model_name_groups[key[-1]].append(registered_schema)

    def get(self, key: tuple[str, ...]) -> RegisteredSchema:
        return self._schema_key_map[key]

    def from_reference(self, reference: Reference) -> RegisteredSchema:
        return self._schema_reference_map[id(reference)]

    def __iter__(self) -> Iterator[RegisteredSchema]:
        return iter(self._schema_key_map.values())

    @staticmethod
    def set_reference_paths(name: str, registered_schema: RegisteredSchema) -> None:
        for reference in registered_schema.references:
            reference.ref = f"#/components/schemas/{name}"

    @staticmethod
    def remove_common_prefix(tuples: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
        def longest_common_prefix(tuples_: list[tuple[str, ...]]) -> tuple[str, ...]:
            if not tuples_:
                return ()

            prefix_ = tuples_[0]
            for t in tuples_:
                # Compare the current prefix with each tuple and shorten it
                prefix_ = prefix_[: min(len(prefix_), len(t))]
                for i in range(len(prefix_)):
                    if prefix_[i] != t[i]:
                        prefix_ = prefix_[:i]
                        break
            return prefix_

        prefix = longest_common_prefix(tuples)
        prefix_length = len(prefix)
        return [t[prefix_length:] for t in tuples]

    def generate_components_schemas(self) -> dict[str, Schema]:
        components_schemas: dict[str, Schema] = {}

        for name, name_group in self._model_name_groups.items():
            if len(name_group) == 1:
                self.set_reference_paths(name, name_group[0])
                components_schemas[name] = name_group[0].schema
                continue

            full_keys = [registered_schema.key for registered_schema in name_group]
            names = ["_".join(k) for k in self.remove_common_prefix(full_keys)]
            for name_, registered_schema in zip(names, name_group):
                self.set_reference_paths(name_, registered_schema)
                components_schemas[name_] = registered_schema.schema

        return components_schemas


class OpenAPIContext:
    def __init__(
        self,
        openapi_config: OpenAPIConfig,
        plugins: Sequence[OpenAPISchemaPluginProtocol],
        schemas: dict[str, Schema],
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
                "operation_ids must be unique, "
                f"please ensure the value of 'operation_id' is either not set or unique for {operation_id}"
            )
        self.operation_ids.add(operation_id)
