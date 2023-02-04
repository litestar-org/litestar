from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Set, Union, cast

from msgspec import UNSET, Struct, from_builtins
from msgspec import ValidationError as MsgspecValidationException
from msgspec.inspect import type_info
from pydantic import BaseConfig, BaseModel
from pydantic import ValidationError as PydanticValidationException

from starlite.enums import ScopeType
from starlite.exceptions import InternalServerException, ValidationException
from starlite.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from starlite.plugins import PluginMapping
from starlite.signature.field import SignatureField
from starlite.types import Empty

if TYPE_CHECKING:
    from msgspec.inspect import StructType

    from starlite.connection import ASGIConnection, Request


class MsgSpecSignatureModel(Struct):
    """Msgspec Struct used to model callables that do not use any pydantic specific type or types."""

    dependency_name_set: ClassVar[Set[str]]
    expected_reserved_kwargs: ClassVar[Set[str]]
    field_plugin_mappings: ClassVar[Dict[str, PluginMapping]]
    return_annotation: ClassVar[Any]
    signature_fields: ClassVar[Dict[str, Any]]

    @classmethod
    def fields(cls) -> Dict[str, "SignatureField"]:
        """Allow uniform access to the signature models fields, independent of the implementation.

        Returns:
            A string keyed mapping of field values.
        """
        return cls.signature_fields

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
            signature = from_builtins(kwargs, cls)
        except MsgspecValidationException as e:
            method = (
                cast("Request[Any,Any,Any]", connection).method.lower()
                if connection.scope["type"] == ScopeType.HTTP
                else ScopeType.WEBSOCKET.value
            )
            raise ValidationException(detail=f"Validation failed for {method} connection {connection.url}") from e

        return signature.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
        """
        return {k: getattr(self, k) for k in self.signature_fields}

    @classmethod
    def populate_signature_fields(cls) -> None:
        """Populate the class signature fields.

        Returns:
            None.
        """

        data = cast("StructType", type_info(cls))
        cls.signature_fields = {}

        for field in data.fields:
            field_type = cls.__annotations__[field.name]
            kwargs_model: Optional[Union[ParameterKwarg, DependencyKwarg, BodyKwarg]] = None
            default_value: Any = field.default if field.default is not UNSET else Empty

            if isinstance(default_value, (ParameterKwarg, DependencyKwarg, BodyKwarg)):
                kwargs_model = default_value
                default_value = default_value.default

            cls.signature_fields[field.name] = SignatureField.create(
                field_type=field_type, name=field.name, default_value=default_value, kwarg_model=kwargs_model, extra={}
            )


class PydanticSignatureModel(BaseModel):
    """Pydantic Model used to model callables that use at least one pydantic specific type."""

    dependency_name_set: ClassVar[Set[str]]
    expected_reserved_kwargs: ClassVar[Set[str]]
    field_plugin_mappings: ClassVar[Dict[str, PluginMapping]]
    return_annotation: ClassVar[Any]
    signature_fields: ClassVar[Dict[str, Any]]

    class Config(BaseConfig):
        copy_on_model_validation = "none"
        arbitrary_types_allowed = True

    @classmethod
    def fields(cls) -> Dict[str, "SignatureField"]:
        """Allow uniform access to the signature models fields, independent of the implementation.

        Returns:
            A string keyed mapping of field values.
        """
        return cls.signature_fields

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
        except PydanticValidationException as e:
            method = (
                cast("Request[Any,Any,Any]", connection).method.lower()
                if connection.scope["type"] == ScopeType.HTTP
                else ScopeType.WEBSOCKET.value
            )
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


SignatureModel = Union[PydanticSignatureModel, MsgSpecSignatureModel]
