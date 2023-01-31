from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Optional, Set, Tuple, Union

from pydantic import BaseConfig, BaseModel, ValidationError
from pydantic.fields import ModelField
from typing_extensions import get_args, get_origin

from starlite.connection import ASGIConnection, Request
from starlite.constants import UNDEFINED_SENTINELS
from starlite.enums import ScopeType
from starlite.exceptions import InternalServerException, ValidationException
from starlite.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from starlite.plugins import PluginMapping
from starlite.types import Empty
from starlite.utils import is_any, is_optional_union, is_union, make_non_optional_union
from starlite.utils.predicates import (
    is_generic,
    is_mapping,
    is_non_string_iterable,
    is_non_string_sequence,
)


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

    children: Optional[Tuple["SignatureField", ...]]
    """A mapping of subtypes, if any."""
    default_value: Any
    """Field name."""
    extra: Dict[str, Any]
    """A mapping of extra values."""
    field_type: Any
    """The type of the kwarg."""
    kwarg_model: Optional[Union[ParameterKwarg, BodyKwarg, DependencyKwarg]]
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

    @classmethod
    def create(
        cls,
        field_type: Any,
        name: str = "",
        default_value: Any = Empty,
        children: Optional[Tuple["SignatureField", ...]] = None,
        kwarg_model: Optional[Union[ParameterKwarg, BodyKwarg, DependencyKwarg]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> "SignatureField":
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

    @classmethod
    def from_model_field(cls, model_field: ModelField) -> "SignatureField":
        """Create a SignatureField instance from a pydantic ModelField.

        Args:
            model_field: A pydantic ModelField instance.

        Returns:
            A SignatureField
        """
        children = (
            tuple(cls.from_model_field(sub_field) for sub_field in model_field.sub_fields)
            if model_field.sub_fields
            else None
        )
        default_value = (
            model_field.field_info.default if model_field.field_info.default not in UNDEFINED_SENTINELS else Empty
        )

        kwarg_model: Optional[Union[ParameterKwarg, DependencyKwarg, BodyKwarg]] = model_field.field_info.extra.pop(
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


class SignatureModel(ABC):
    """Base model for Signature modelling."""

    dependency_name_set: ClassVar[Set[str]]
    field_plugin_mappings: ClassVar[Dict[str, PluginMapping]]
    return_annotation: ClassVar[Any]
    signature_fields: Dict[str, SignatureField]

    @classmethod
    @abstractmethod
    def parse_values_from_connection_kwargs(cls, connection: "ASGIConnection", **kwargs: Any) -> Dict[str, Any]:
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

    @classmethod
    def fields(cls) -> Dict[str, SignatureField]:
        """Allow uniform access to the signature models fields, independent of the implementation.

        Returns:
            A string keyed mapping of field values.
        """
        return cls.signature_fields

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
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
    def parse_values_from_connection_kwargs(cls, connection: "ASGIConnection", **kwargs: Any) -> Dict[str, Any]:
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
        value = self.__getattribute__(key)  # pylint: disable=unnecessary-dunder-call
        mapping = self.field_plugin_mappings.get(key)
        return mapping.get_model_instance_for_value(value) if mapping else value

    def to_dict(self) -> Dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
        """
        if self.field_plugin_mappings:
            return {key: self._resolve_field_value(key) for key in self.__fields__}
        return {key: self.__getattribute__(key) for key in self.__fields__}  # pylint: disable=unnecessary-dunder-call

    @classmethod
    def populate_signature_fields(cls) -> None:
        """Populate the class signature fields.

        Returns:
            None.
        """
        cls.signature_fields = {k: SignatureField.from_model_field(v) for k, v in cls.__fields__.items()}
