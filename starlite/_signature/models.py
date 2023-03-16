from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseConfig, BaseModel, ValidationError
from typing_extensions import get_args, get_origin

from starlite.connection import ASGIConnection, Request
from starlite.constants import UNDEFINED_SENTINELS
from starlite.dto import AbstractDTO
from starlite.enums import ScopeType
from starlite.exceptions import InternalServerException, ValidationException
from starlite.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from starlite.types import Empty
from starlite.utils import is_any, is_optional_union, is_union, make_non_optional_union
from starlite.utils.predicates import (
    is_class_and_subclass,
    is_generic,
    is_mapping,
    is_non_string_iterable,
    is_non_string_sequence,
)

if TYPE_CHECKING:
    from typing import ClassVar

    from .parsing import ParsedSignatureParameter

__all__ = ("PydanticSignatureModel", "SignatureField", "SignatureModel")

if TYPE_CHECKING:
    from pydantic.fields import ModelField

    from starlite.plugins import PluginMapping


@dataclass(unsafe_hash=True, frozen=True)
class SignatureField:
    """Abstraction representing a model field. This class is meant to replace equivalent datastructures from, other
    libraries, for example, pydantic or msgspec.
    """

    __slots__ = (
        "children",
        "default_value",
        "extra",
        "field_type",
        "kwarg_model",
        "name",
    )

    children: tuple[SignatureField, ...] | None
    """A mapping of subtypes, if any."""
    default_value: Any
    """Field name."""
    extra: dict[str, Any]
    """A mapping of extra values."""
    field_type: Any
    """The type of the kwarg."""
    kwarg_model: ParameterKwarg | BodyKwarg | DependencyKwarg | None
    """Kwarg Parameter."""
    name: str
    """Field name."""

    @property
    def is_empty(self) -> bool:
        """Check if the default value is an empty type.

        Returns:
            True if the default_value is Empty or Ellipsis otherwise False.
        """
        return self.default_value is Empty or self.default_value is Ellipsis

    @property
    def is_optional(self) -> bool:
        """Check if the field type is an Optional union.

        Returns:
            True if the field_type is an Optional union otherwise False.
        """
        return is_optional_union(self.field_type)

    @property
    def is_mapping(self) -> bool:
        """Check if the field type is a Mapping."""
        return is_mapping(self.field_type)

    @property
    def is_non_string_iterable(self) -> bool:
        """Check if the field type is an Iterable.

        If ``self.field_type`` is an optional union, only the non-optional members of the union are evaluated.

        See: https://github.com/starlite-api/starlite/issues/1106
        """
        field_type = self.field_type
        if self.is_optional:
            field_type = make_non_optional_union(field_type)
        return is_non_string_iterable(field_type)

    @property
    def is_non_string_sequence(self) -> bool:
        """Check if the field type is a non-string Sequence.

        If ``self.field_type`` is an optional union, only the non-optional members of the union are evaluated.

        See: https://github.com/starlite-api/starlite/issues/1106
        """
        field_type = self.field_type
        if self.is_optional:
            field_type = make_non_optional_union(field_type)
        return is_non_string_sequence(field_type)

    @property
    def is_any(self) -> bool:
        """Check if the field type is Any."""
        return is_any(self.field_type)

    @property
    def is_union(self) -> bool:
        """Check if the field type is a Union."""
        return is_union(self.field_type)

    @property
    def is_generic(self) -> bool:
        """Check if the field type is a custom class extending Generic."""
        return is_generic(self.field_type)

    @property
    def is_simple_type(self) -> bool:
        """Check if the field type is a singleton value (e.g. int, str etc.)."""
        return not (
            self.is_generic or self.is_optional or self.is_union or self.is_mapping or self.is_non_string_iterable
        )

    @property
    def is_parameter_field(self) -> bool:
        """Check if the field type is a parameter kwarg value."""
        return self.kwarg_model is not None and isinstance(self.kwarg_model, ParameterKwarg)

    @property
    def is_const(self) -> bool:
        """Check if the field is defined as constant value."""
        return bool(self.kwarg_model and getattr(self.kwarg_model, "const", False))

    @property
    def is_required(self) -> bool:
        """Check if the field should be marked as a required parameter."""
        if isinstance(self.kwarg_model, ParameterKwarg) and self.kwarg_model.required is not None:
            return self.kwarg_model.required

        return not (self.is_optional or self.is_any) and (self.is_empty or self.default_value is None)

    @property
    def is_literal(self) -> bool:
        """Check if the field type is Literal."""
        return get_origin(self.field_type) is Literal

    @property
    def parsed_parameter(self) -> ParsedSignatureParameter:
        """The associated _signature.parsing.ParsedSignatureParameter type."""
        return self.extra["parsed_parameter"]  # type:ignore[no-any-return]

    @property
    def has_dto_annotation(self) -> bool:
        """Field is annotated with a DTO type."""
        return is_class_and_subclass(self.parsed_parameter.annotation, AbstractDTO)  # type:ignore[type-abstract]

    @classmethod
    def create(
        cls,
        field_type: Any,
        name: str = "",
        default_value: Any = Empty,
        children: tuple[SignatureField, ...] | None = None,
        kwarg_model: ParameterKwarg | BodyKwarg | DependencyKwarg | None = None,
        extra: dict[str, Any] | None = None,
    ) -> SignatureField:
        """Create a new SignatureModel instance.

        Args:
            field_type: The type of the kwarg.
            name: Field name.
            default_value: A default value.
            children: A mapping of subtypes, if any.
            kwarg_model: Kwarg Parameter.
            extra: A mapping of extra values.

        Returns:
            SignatureField instance.
        """
        if kwarg_model and default_value is Empty:
            default_value = kwarg_model.default

        if not children and get_origin(field_type) and (type_args := get_args(field_type)):
            children = tuple(SignatureField.create(arg) for arg in type_args)

        return SignatureField(
            name=name,
            field_type=field_type if field_type is not Empty else Any,
            default_value=default_value if default_value not in UNDEFINED_SENTINELS else Empty,
            children=children,
            kwarg_model=kwarg_model,
            extra=extra or {},
        )


class SignatureModel(ABC):
    """Base model for Signature modelling."""

    dependency_name_set: ClassVar[set[str]]
    field_plugin_mappings: ClassVar[dict[str, PluginMapping]]
    return_annotation: ClassVar[Any]
    return_dto: ClassVar[type[AbstractDTO] | None]
    fields: ClassVar[dict[str, SignatureField]]

    @classmethod
    @abstractmethod
    def parse_values_from_connection_kwargs(cls, connection: ASGIConnection, **kwargs: Any) -> dict[str, Any]:
        """Extract values from the connection instance and return a dict of parsed values.

        Args:
            connection: The ASGI connection instance.
            **kwargs: A dictionary of kwargs.

        Raises:
            ValidationException: If validation failed.
            InternalServerException: If another exception has been raised.

        Returns:
            A dictionary of parsed values
        """
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def populate_signature_fields(cls) -> None:
        """Populate the class signature fields.

        Returns:
            None.
        """
        raise NotImplementedError


class PydanticSignatureModel(SignatureModel, BaseModel):
    """Model that represents a function signature that uses a pydantic specific type or types."""

    class Config(BaseConfig):
        copy_on_model_validation = "none"
        arbitrary_types_allowed = True

    @classmethod
    def parse_values_from_connection_kwargs(cls, connection: ASGIConnection, **kwargs: Any) -> dict[str, Any]:
        """Extract values from the connection instance and return a dict of parsed values.

        Args:
            connection: The ASGI connection instance.
            **kwargs: A dictionary of kwargs.

        Raises:
            ValidationException: If validation failed.
            InternalServerException: If another exception has been raised.

        Returns:
            A dictionary of parsed values
        """
        try:
            signature = cls(**kwargs)
        except ValidationError as e:
            method = connection.method if isinstance(connection, Request) else ScopeType.WEBSOCKET
            if client_errors := [error for error in e.errors() if error["loc"][-1] not in cls.dependency_name_set]:
                raise ValidationException(
                    detail=f"Validation failed for {method} {connection.url}", extra=client_errors
                ) from e
            raise InternalServerException(
                detail=f"A dependency failed validation for {method} {connection.url}", extra=e.errors()
            ) from e

        return signature.to_dict()

    def _resolve_field_value(self, key: str) -> Any:
        """Return value using key mapping, if available.

        Args:
            key: A field name.

        Returns:
            The plugin value, if available.
        """
        value = self.__getattribute__(key)
        mapping = self.field_plugin_mappings.get(key)
        return mapping.get_model_instance_for_value(value) if mapping else value

    def to_dict(self) -> dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
        """
        if self.field_plugin_mappings:
            return {key: self._resolve_field_value(key) for key in self.__fields__}
        return {key: self.__getattribute__(key) for key in self.__fields__}

    @classmethod
    def signature_field_from_model_field(cls, model_field: ModelField) -> SignatureField:
        """Create a SignatureField instance from a pydantic ModelField.

        Args:
            model_field: A pydantic ModelField instance.

        Returns:
            A SignatureField
        """
        children = (
            tuple(cls.signature_field_from_model_field(sub_field) for sub_field in model_field.sub_fields)
            if model_field.sub_fields
            else None
        )
        default_value = (
            model_field.field_info.default if model_field.field_info.default not in UNDEFINED_SENTINELS else Empty
        )

        kwarg_model: ParameterKwarg | DependencyKwarg | BodyKwarg | None = model_field.field_info.extra.pop(
            "kwargs_model", None
        )
        if kwarg_model:
            default_value = kwarg_model.default
        elif isinstance(default_value, (ParameterKwarg, DependencyKwarg, BodyKwarg)):
            kwarg_model = default_value
            default_value = default_value.default

        return SignatureField(
            children=children,
            default_value=default_value,
            extra=model_field.field_info.extra or {},
            field_type=model_field.annotation if model_field.annotation is not Empty else Any,
            kwarg_model=kwarg_model,
            name=model_field.name,
        )

    @classmethod
    def populate_signature_fields(cls) -> None:
        """Populate the class signature fields.

        Returns:
            None.
        """
        cls.fields = {k: cls.signature_field_from_model_field(v) for k, v in cls.__fields__.items()}
