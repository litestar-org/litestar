from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Set

from pydantic import BaseConfig, BaseModel, ValidationError

from starlite.connection import ASGIConnection, Request
from starlite.enums import ScopeType
from starlite.exceptions import InternalServerException, ValidationException
from starlite.plugins import PluginMapping


class SignatureModel(ABC):
    """Base model for Signature modelling."""

    dependency_name_set: ClassVar[Set[str]]
    field_plugin_mappings: ClassVar[Dict[str, PluginMapping]]
    return_annotation: ClassVar[Any]

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
    @abstractmethod
    def fields(cls) -> Dict[str, Any]:
        """Allow uniform access to the signature models fields, independent of the implementation.

        Returns:
            A string keyed mapping of field values.
        """
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
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

    @classmethod
    def fields(cls) -> Dict[str, Any]:
        """Allow uniform access to the signature models fields, independent of the implementation.

        Returns:
            A string keyed mapping of field values.
        """
        return dict(cls.__fields__)

    def to_dict(self) -> Dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
        """
        if self.field_plugin_mappings:
            return {key: self._resolve_field_value(key) for key in self.__fields__}
        return {key: self.__getattribute__(key) for key in self.__fields__}  # pylint: disable=unnecessary-dunder-call
