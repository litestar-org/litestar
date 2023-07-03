from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar.typing import ParsedType

if TYPE_CHECKING:
    from typing import Any, Callable

    from litestar.dto.factory import DTOField
    from litestar.dto.factory._backends.abc import AbstractDTOBackend
    from litestar.dto.types import ForType

T = TypeVar("T")


class DTOData(Generic[T]):
    """DTO validated data and utility methods."""

    __slots__ = ("_backend", "_data_as_builtins")

    def __init__(self, backend: AbstractDTOBackend[Any], data_as_builtins: Any) -> None:
        self._backend = backend
        self._data_as_builtins = data_as_builtins

    def create_instance(self, **kwargs: Any) -> T:
        """Create an instance of the DTO validated data.

        Args:
            **kwargs: Additional data to create the instance with. Takes precedence over DTO validated data.
        """
        data = dict(self._data_as_builtins)
        for k, v in kwargs.items():
            _set_nested_dict_value(data, k.split("__"), v)
        return self._backend.transfer_data_from_builtins(data)  # type:ignore[no-any-return]

    def update_instance(self, instance: T, **kwargs: Any) -> T:
        """Update an instance with the DTO validated data.

        Args:
            instance: The instance to update.
            **kwargs: Additional data to update the instance with. Takes precedence over DTO validated data.
        """
        data = {**self._data_as_builtins, **kwargs}
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def as_builtins(self) -> Any:
        """Return the DTO validated data as builtins."""
        return self._data_as_builtins


def _set_nested_dict_value(d: dict[str, Any], keys: list[str], value: Any) -> None:
    if len(keys) == 1:
        d[keys[0]] = value
    else:
        key = keys[0]
        d.setdefault(key, {})
        _set_nested_dict_value(d[key], keys[1:], value)


@dataclass(frozen=True)
class FieldDefinition(ParsedType):
    """A model field representation for purposes of generating a DTO backend model type."""

    __slots__ = (
        "default_factory",
        "dto_field",
        "dto_for",
        "unique_model_name",
    )

    unique_model_name: str
    """Unique identifier of model that owns the field."""
    default_factory: Callable[[], Any] | None
    """Default factory of the field."""
    dto_field: DTOField
    """DTO field configuration."""
    dto_for: ForType | None
    """Direction of transfer for field.

    Specify if the field definition should only be added to models for only the request (``"data"``) or response
    (``"return"``). If there should be no such distinction, set to ``None``.

    This is to support special cases where the type to set an attribute may be different to the type received when
    retrieving its value. For example, a :class:`sqlalchemy.ext.hybrid.hybrid_property` may be set with a ``str`` but
    retrieved as some other type.

    The difference between this, and marking a field as read-only or private, is that it cannot be overridden by the end
    user.
    """

    def unique_name(self) -> str:
        return f"{self.unique_model_name}.{self.name}"

    @classmethod
    def from_parsed_type(
        cls,
        parsed_type: ParsedType,
        unique_model_name: str,
        default_factory: Callable[[], Any] | None,
        dto_field: DTOField,
        dto_for: ForType | None,
    ) -> FieldDefinition:
        """Create a :class:`FieldDefinition` from a :class:`ParsedType`.

        Args:
            parsed_type: A :class:`ParsedType` to create a :class:`FieldDefinition` from.
            unique_model_name: The unique name of the model.
            default_factory: Default factory function, if any.
            dto_field: DTOField instance.
            dto_for: DTO type.

        Returns:
            A :class:`FieldDefinition` instance.
        """
        return FieldDefinition(
            annotation=parsed_type.annotation,
            args=parsed_type.args,
            default=parsed_type.default,
            extra=parsed_type.extra,
            inner_types=parsed_type.inner_types,
            instantiable_origin=parsed_type.instantiable_origin,
            kwarg_definition=parsed_type.kwarg_definition,
            metadata=parsed_type.metadata,
            name=parsed_type.name,
            origin=parsed_type.origin,
            raw=parsed_type.raw,
            safe_generic_origin=parsed_type.safe_generic_origin,
            type_wrappers=parsed_type.type_wrappers,
            unique_model_name=unique_model_name,
            default_factory=default_factory,
            dto_field=dto_field,
            dto_for=dto_for,
        )
