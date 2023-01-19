from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import Any, ClassVar, Dict, Optional, Set, Tuple, Union

from pydantic import BaseConfig, BaseModel, ValidationError
from pydantic.fields import ModelField, Undefined

from starlite.connection import ASGIConnection, Request
from starlite.enums import ScopeType
from starlite.exceptions import InternalServerException, ValidationException
from starlite.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from starlite.plugins import PluginMapping
from starlite.types import Empty
from starlite.utils import is_any, is_optional_union, is_union
from starlite.utils.predicates import (
    is_generic,
    is_mapping,
    is_non_string_iterable,
    is_non_string_sequence,
)


@dataclass(unsafe_hash=True, frozen=True)
class SignatureField:
    """Abstraction replacing both the pydantic and msgspec equivalent data structures."""

    __slots__ = (
        "children",
        "default_value",
        "extra",
        "field_type",
        "kwarg_model",
    )

    children: Optional[Tuple["SignatureField", ...]]
    default_value: Any
    extra: Dict[str, Any]
    field_type: Any
    kwarg_model: Optional[Union[ParameterKwarg, BodyKwarg, DependencyKwarg]]

    @cached_property
    def is_optional(self) -> bool:
        """Check if the field type is an Optional union.

        Returns:
            True if the field_type is an Optional union otherwise False.
        """
        return is_optional_union(self.field_type)

    @cached_property
    def is_mapping(self) -> bool:
        """Check if the field type is a Mapping."""
        return is_mapping(self.field_type)

    @cached_property
    def is_iterable(self) -> bool:
        """Check if the field type is an Iterable."""
        return is_non_string_iterable(self.field_type)

    @cached_property
    def is_sequence(self) -> bool:
        """Check if the field type is a non-string Sequence."""
        return is_non_string_sequence(self.field_type)

    @cached_property
    def is_any(self) -> bool:
        """Check if the field type is Any."""
        return is_any(self.field_type)

    @cached_property
    def is_union(self) -> bool:
        """Check if the field type is a Union."""
        return is_union(self.field_type)

    @cached_property
    def is_generic(self) -> bool:
        """Check if the field type is a Generic TypeVar."""
        return is_generic(self.field_type)

    @cached_property
    def is_singleton(self) -> bool:
        """Check if the field type is a singleton value (e.g. int, str etc.)."""
        return not (self.is_generic or self.is_optional or self.is_union or self.is_mapping or self.is_iterable)

    @cached_property
    def is_parameter_field(self) -> bool:
        """Check if the field type is a parameter kwarg value."""
        return self.kwarg_model is not None and isinstance(self.kwarg_model, ParameterKwarg)

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
            model_field.field_info.default if model_field.field_info.default not in {Undefined, Ellipsis} else Empty
        )

        kwarg_model: Optional[Union[ParameterKwarg, DependencyKwarg, BodyKwarg]] = None
        if isinstance(default_value, (ParameterKwarg, DependencyKwarg, BodyKwarg)):
            kwarg_model = default_value
            default_value = default_value.default

        return SignatureField(
            children=children,
            default_value=default_value,
            extra=model_field.field_info.extra or {},
            field_type=model_field.type_,
            kwarg_model=kwarg_model,
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
