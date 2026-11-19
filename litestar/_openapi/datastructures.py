from __future__ import annotations

import itertools
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, _GenericAlias, _type_repr, get_origin  # type: ignore[attr-defined]

from litestar._openapi.utils import default_schema_component_name_creator, get_parametrized_generic_class
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec import Reference, Schema
from litestar.params import KwargDefinition
from litestar.typing import TypeAliasTypes

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    from litestar.openapi import OpenAPIConfig
    from litestar.plugins import OpenAPISchemaPlugin
    from litestar.typing import FieldDefinition


INVALID_KEY_CHARACTER_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")


def _longest_common_prefix(tuples_: list[tuple[str, ...]]) -> tuple[str, ...]:
    """Find the longest common prefix of a list of tuples.

    Args:
        tuples_: A list of tuples to find the longest common prefix of.

    Returns:
        The longest common prefix of the tuples.
    """
    prefix_ = tuples_[0]
    for t in tuples_:
        # Compare the current prefix with each tuple and shorten it
        prefix_ = prefix_[: min(len(prefix_), len(t))]
        for i in range(len(prefix_)):
            if prefix_[i] != t[i]:
                prefix_ = prefix_[:i]
                break
    return prefix_


def _get_component_key_override(field: FieldDefinition) -> str | None:
    if (
        (kwarg_definition := field.kwarg_definition)
        and isinstance(kwarg_definition, KwargDefinition)
        and (schema_key := kwarg_definition.schema_component_key)
    ):
        return schema_key
    return None


def _get_normalized_schema_key(field_definition: FieldDefinition) -> tuple[str, ...]:
    """Create a key for a type annotation.

    The key should be a tuple such as ``("path", "to", "type", "TypeName")``.

    Args:
        field_definition: Field definition

    Returns:
        A tuple of strings.
    """
    if override := _get_component_key_override(field_definition):
        return (override,)

    annotation = field_definition.annotation
    module = getattr(annotation, "__module__", "")
    if isinstance(get_origin(annotation) or annotation, TypeAliasTypes):
        name = repr(annotation)
    elif isinstance(annotation, _GenericAlias):
        name = str(annotation)[len(module) + 1 :]
    elif generic := get_parametrized_generic_class(annotation):
        name = f"{generic[0].__qualname__}[{', '.join(_type_repr(arg) for arg in generic[1])}]"
    else:
        name = annotation.__qualname__
    name = name.replace(".<locals>.", ".")
    return *module.split("."), re.sub(INVALID_KEY_CHARACTER_PATTERN, "_", name)


_DTO_TRANSFER_MODEL_MODULE = "litestar.dto._backend"


def _is_same_type(existing: FieldDefinition, field: FieldDefinition) -> bool:
    if existing.origin or field.origin:
        return (
            existing.origin == field.origin
            and len(existing.inner_types) == len(field.inner_types)
            and all(map(_is_same_type, existing.inner_types, field.inner_types))
        )
    if existing.annotation == field.annotation:
        return True
    return (
        getattr(existing.annotation, "__module__", None) == _DTO_TRANSFER_MODEL_MODULE
        and getattr(field.annotation, "__module__", None) == _DTO_TRANSFER_MODEL_MODULE
        and existing.annotation.__qualname__ == field.annotation.__qualname__
    )


def _without_examples(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _without_examples(v) for k, v in value.items() if k != "examples" or not isinstance(v, list)}
    if isinstance(value, list):
        return [_without_examples(v) for v in value]
    return value


@dataclass(eq=False)
class RegisteredSchema:
    """Object to store a schema and any references to it."""

    key: tuple[str, ...]
    """The key used to register the schema."""
    schema: Schema
    references: list[Reference]
    name: str
    """The preferred name of the schema in the components/schemas section."""
    field_definition: FieldDefinition
    """The type the schema describes."""


class SchemaRegistry:
    """A registry for object schemas.

    This class is used to store schemas that we reference from other parts of the spec.

    Its main purpose is to allow us to generate the components/schemas section of the spec once we have
    collected all the schemas that should be included.

    This allows us to determine a path to the schema in the components/schemas section of the spec that
    is unique and as short as possible.
    """

    def __init__(
        self,
        name_creator: Callable[[FieldDefinition], str] = default_schema_component_name_creator,
        ignore_examples: bool = False,
    ) -> None:
        """Create a new SchemaRegistry.

        Args:
            name_creator: A callable returning the preferred component name of a type.
            ignore_examples: Whether ``examples`` are left out when same-named classes are compared.
        """
        self._name_creator = name_creator
        self._ignore_examples = ignore_examples
        self._schema_key_map: dict[tuple[str, ...], list[RegisteredSchema]] = {}
        self._schema_reference_map: dict[int, RegisteredSchema] = {}
        self._schema_id_map: dict[int, RegisteredSchema] = {}
        self._model_name_groups: defaultdict[str, list[RegisteredSchema]] = defaultdict(list)

    def _get_registered_schema(self, key: tuple[str, ...], field: FieldDefinition) -> RegisteredSchema | None:
        registered_schemas = self._schema_key_map.get(key, [])
        for registered_schema in registered_schemas:
            if _is_same_type(registered_schema.field_definition, field):
                return registered_schema
        if registered_schemas and _get_component_key_override(field):
            existing = registered_schemas[0].field_definition
            if f"{field.raw!r}" != f"{existing.raw!r}":
                raise ImproperlyConfiguredException(
                    f"Schema component keys must be unique. The 'schema_component_key' {key[0]!r} of the type "
                    f"{field.raw!r} is already used by a different type {existing.raw!r}."
                )
        return None

    def get_schema_for_field_definition(self, field: FieldDefinition) -> Schema:
        """Get a registered schema by its key.

        Args:
            field: The field definition to get the schema for

        Returns:
            A RegisteredSchema object.
        """
        key = _get_normalized_schema_key(field)
        if (registered_schema := self._get_registered_schema(key, field)) is None:
            name = _get_component_key_override(field) or re.sub(
                INVALID_KEY_CHARACTER_PATTERN, "_", self._name_creator(field)
            )
            registered_schema = RegisteredSchema(key, Schema(), [], name=name, field_definition=field)
            registered_schemas = self._schema_key_map.setdefault(key, [])
            if all(r.name != name for r in registered_schemas):
                self._model_name_groups[name].append(registered_schema)
            registered_schemas.append(registered_schema)
            self._schema_id_map[id(registered_schema.schema)] = registered_schema
        return registered_schema.schema

    def get_reference_for_field_definition(self, field: FieldDefinition) -> Reference | None:
        """Get a reference to a registered schema by its key.

        Args:
            field: The field definition to get the reference for

        Returns:
            A Reference object.
        """
        registered_schema = self._get_registered_schema(_get_normalized_schema_key(field), field)
        return None if registered_schema is None else self._create_reference(registered_schema)

    def get_reference_for_schema(self, schema: Schema) -> Reference | None:
        """Get a reference to ``schema`` if it is a registered component schema.

        Args:
            schema: The schema to get the reference for

        Returns:
            A Reference object, or ``None`` if the schema is not registered.
        """
        if (registered_schema := self._schema_id_map.get(id(schema))) is None:
            return None
        return self._create_reference(registered_schema)

    def _create_reference(self, registered_schema: RegisteredSchema) -> Reference:
        reference = Reference(f"#/components/schemas/{'_'.join(registered_schema.key)}")
        registered_schema.references.append(reference)
        self._schema_reference_map[id(reference)] = registered_schema
        return reference

    def from_reference(self, reference: Reference) -> RegisteredSchema:
        """Get a registered schema by its reference.

        Args:
            reference: The reference to the schema to get.

        Returns:
            A RegisteredSchema object.
        """
        return self._schema_reference_map[id(reference)]

    def __iter__(self) -> Iterator[RegisteredSchema]:
        """Iterate over the registered schemas."""
        return itertools.chain.from_iterable(self._schema_key_map.values())

    @staticmethod
    def set_reference_paths(name: str, registered_schema: RegisteredSchema) -> None:
        """Set the reference paths for a registered schema."""
        for reference in registered_schema.references:
            reference.ref = f"#/components/schemas/{name}"

    @staticmethod
    def remove_common_prefix(tuples: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
        """Remove the common prefix from a list of tuples.

        Args:
            tuples: A list of tuples to remove the common prefix from.

        Returns:
            A list of tuples with the common prefix removed.
        """

        prefix = _longest_common_prefix(tuples)
        prefix_length = len(prefix)
        return [t[prefix_length:] for t in tuples]

    def _render(self, registered_schema: RegisteredSchema) -> str:
        schema = registered_schema.schema.to_schema()
        return json.dumps(_without_examples(schema) if self._ignore_examples else schema, sort_keys=True, default=str)

    def _group_same_key_schemas(self) -> dict[tuple[tuple[str, ...], str], list[list[RegisteredSchema]]]:
        entries = [r for schemas in self._schema_key_map.values() if len(schemas) > 1 for r in schemas]
        initial: dict[tuple[tuple[str, ...], str], int] = {}
        labels = {id(r): initial.setdefault((r.key, r.name), len(initial)) for r in entries}
        count = len(initial)
        while True:
            for registered_schema in entries:
                self.set_reference_paths(f"#{labels[id(registered_schema)]}", registered_schema)
            signatures: dict[tuple[int, str], int] = {}
            labels = {id(r): signatures.setdefault((labels[id(r)], self._render(r)), len(signatures)) for r in entries}
            if len(signatures) == count:
                break
            count = len(signatures)

        groups: dict[tuple[tuple[str, ...], str], dict[int, list[RegisteredSchema]]] = {}
        for r in entries:
            groups.setdefault((r.key, r.name), {}).setdefault(labels[id(r)], []).append(r)
        return {key: list(members.values()) for key, members in groups.items()}

    def generate_components_schemas(self) -> dict[str, Schema]:
        """Generate the components/schemas section of the spec.

        Returns:
            A dictionary of schemas.
        """
        components_schemas: dict[str, Schema] = {}
        same_key_groups = self._group_same_key_schemas()

        named_schemas: list[tuple[str, RegisteredSchema]] = [
            (name, name_group[0]) for name, name_group in self._model_name_groups.items() if len(name_group) == 1
        ]
        for name_group in self._model_name_groups.values():
            if len(name_group) == 1:
                continue

            names = ["_".join(k) for k in self.remove_common_prefix([(*r.key[:-1], r.name) for r in name_group])]
            if len(set(names)) != len(names) or "" in names:
                names = ["_".join(k) for k in self.remove_common_prefix([r.key for r in name_group])]
            named_schemas.extend(zip(names, name_group, strict=True))

        numbered_schemas: list[tuple[str, list[RegisteredSchema]]] = []
        for name, registered_schema in named_schemas:
            if not name or name in components_schemas:
                name = "_".join(registered_schema.key)
            if name in components_schemas:
                raise ImproperlyConfiguredException(
                    f"Schema component names must be unique. The name {name!r} of type "
                    f"{registered_schema.field_definition.raw!r} is already used by another type."
                )
            group, *other_groups = same_key_groups.get(
                (registered_schema.key, registered_schema.name), [[registered_schema]]
            )
            if other_groups and _get_component_key_override(registered_schema.field_definition):
                raise ImproperlyConfiguredException(
                    f"Schema component keys must be unique. The 'schema_component_key' {name!r} is used by "
                    f"{len(other_groups) + 1} different types {registered_schema.field_definition.raw!r}."
                )
            numbered_schemas.extend((name, other_group) for other_group in other_groups)
            self._add_component(name, group, components_schemas)

        for base_name, group in numbered_schemas:
            name = next(n for i in itertools.count(2) if (n := f"{base_name}_{i}") not in components_schemas)
            self._add_component(name, group, components_schemas)

        # Sort them by name to ensure they're always generated in the same order.
        return {name: components_schemas[name] for name in sorted(components_schemas.keys())}

    def _add_component(self, name: str, group: list[RegisteredSchema], components_schemas: dict[str, Schema]) -> None:
        for registered_schema in group:
            self.set_reference_paths(name, registered_schema)
        components_schemas[name] = group[0].schema


class OpenAPIContext:
    def __init__(
        self,
        openapi_config: OpenAPIConfig,
        plugins: Sequence[OpenAPISchemaPlugin],
    ) -> None:
        self.openapi_config = openapi_config
        self.plugins = plugins
        self.operation_ids: set[str] = set()
        self.schema_registry = SchemaRegistry(
            name_creator=openapi_config.schema_component_name_creator, ignore_examples=openapi_config.create_examples
        )

    def add_operation_id(self, operation_id: str) -> None:
        """Add an operation ID to the context.

        Args:
            operation_id: Operation ID to add.
        """
        if operation_id in self.operation_ids:
            raise ImproperlyConfiguredException(
                "operation_ids must be unique, "
                f"please ensure the value of 'operation_id' is either not set or unique for {operation_id!r}"
            )
        self.operation_ids.add(operation_id)
