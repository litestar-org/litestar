from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from typing import Any, Callable

    from litestar.dto import DTOField
    from litestar.dto._backend import DTOBackend
    from litestar.dto.types import ForType

T = TypeVar("T")


class DTOData(Generic[T]):
    """DTO validated data and utility methods."""

    __slots__ = ("_backend", "_data_as_builtins")

    def __init__(self, backend: DTOBackend, data_as_builtins: Any) -> None:
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
class DTOFieldDefinition(FieldDefinition):
    """A model field representation for purposes of generating a DTO backend model type."""

    __slots__ = (
        "default_factory",
        "dto_field",
        "dto_for",
        "model_name",
    )

    model_name: str
    """The name of the model for which the field is generated."""
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

    @classmethod
    def from_field_definition(
        cls,
        field_definition: FieldDefinition,
        model_name: str,
        default_factory: Callable[[], Any] | None,
        dto_field: DTOField,
        dto_for: ForType | None,
    ) -> DTOFieldDefinition:
        """Create a :class:`FieldDefinition` from a :class:`FieldDefinition`.

        Args:
            field_definition: A :class:`FieldDefinition` to create a :class:`FieldDefinition` from.
            model_name: The name of the model.
            default_factory: Default factory function, if any.
            dto_field: DTOField instance.
            dto_for: DTO type.

        Returns:
            A :class:`FieldDefinition` instance.
        """
        return DTOFieldDefinition(
            annotation=field_definition.annotation,
            args=field_definition.args,
            default=field_definition.default,
            extra=field_definition.extra,
            inner_types=field_definition.inner_types,
            instantiable_origin=field_definition.instantiable_origin,
            kwarg_definition=field_definition.kwarg_definition,
            metadata=field_definition.metadata,
            name=field_definition.name,
            origin=field_definition.origin,
            raw=field_definition.raw,
            safe_generic_origin=field_definition.safe_generic_origin,
            type_wrappers=field_definition.type_wrappers,
            model_name=model_name,
            default_factory=default_factory,
            dto_field=dto_field,
            dto_for=dto_for,
        )
