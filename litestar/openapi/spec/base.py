from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import Enum
from typing import Any

__all__ = ("BaseSchemaObject",)


def _normalize_key(key: str) -> str:
    if key.endswith("_in"):
        return "in"
    if key.startswith("schema_"):
        return key.split("_")[1]
    if "_" in key:
        components = key.split("_")
        return components[0] + "".join(component.title() for component in components[1:])
    if key == "ref":
        return "$ref"
    return key


def _normalize_value(value: Any) -> Any:
    if isinstance(value, BaseSchemaObject):
        return value.to_schema()
    if is_dataclass(value):
        return {_normalize_value(k): _normalize_value(v) for k, v in asdict(value).items() if v is not None}
    if isinstance(value, dict):
        return {_normalize_value(k): _normalize_value(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    return value


@dataclass
class BaseSchemaObject:
    """Base class for schema spec objects"""

    def to_schema(self) -> dict[str, Any]:
        """Transform the spec dataclass object into a string keyed dictionary. This method traverses all nested values
        recursively.
        """
        result: dict[str, Any] = {}

        for field in fields(self):
            value = _normalize_value(getattr(self, field.name, None))

            if value is not None:
                key = _normalize_key(field.name)
                result[key] = value

        return result
