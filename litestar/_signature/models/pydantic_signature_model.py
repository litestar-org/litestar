from __future__ import annotations

from dataclasses import asdict, replace
from typing import TYPE_CHECKING, Any

from pydantic import BaseConfig, BaseModel, ValidationError, create_model
from pydantic.fields import FieldInfo, ModelField

from litestar._signature.models.base import ErrorMessage, SignatureModel
from litestar.constants import UNDEFINED_SENTINELS
from litestar.params import DependencyKwarg
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils.predicates import is_pydantic_constrained_field

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.utils.signature import ParsedSignature

__all__ = ("PydanticSignatureModel",)


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
            messages = cls._get_error_messages(e, connection)
            raise cls._create_exception(messages=messages, connection=connection) from e

        return signature.to_dict()

    def to_dict(self) -> dict[str, Any]:
        """Normalize access to the signature model's dictionary method, because different backends use different methods
        for this.

        Returns: A dictionary of string keyed values.
        """
        return {key: self.__getattribute__(key) for key in self.__fields__}

    @classmethod
    def field_definition_from_model_field(cls, model_field: ModelField) -> FieldDefinition:
        """Create a FieldDefinition instance from a pydantic ModelField.

        Args:
            model_field: A pydantic ModelField instance.

        Returns:
            A FieldDefinition
        """
        inner_types = (
            tuple(cls.field_definition_from_model_field(sub_field) for sub_field in model_field.sub_fields)
            if model_field.sub_fields
            else None
        )

        default = model_field.field_info.default if model_field.field_info.default not in UNDEFINED_SENTINELS else Empty

        return FieldDefinition.from_kwarg(
            inner_types=inner_types,
            default=default,
            extra=model_field.field_info.extra or {},
            annotation=model_field.annotation,
            name=model_field.name,
        )

    @classmethod
    def populate_field_definitions(cls) -> None:
        """Populate the class signature fields.

        Returns:
            None.
        """
        cls.fields = {}

        for field_name, field in cls.__fields__.items():
            field_definition = field.field_info.extra.pop("field_definition")
            default = field.field_info.default if field.field_info.default not in UNDEFINED_SENTINELS else Empty
            if field_definition.is_optional and default is Empty:
                default = None

            cls.fields[field_name] = replace(field_definition, default=default)

    @classmethod
    def create(
        cls,
        fn_name: str,
        fn_module: str | None,
        parsed_signature: ParsedSignature,
        dependency_names: set[str],
        type_overrides: dict[str, Any],
    ) -> type[PydanticSignatureModel]:
        """Create a pydantic based SignatureModel.

        Args:
            fn_name: Name of the callable.
            fn_module: Name of the function's module, if any.
            parsed_signature: A ParsedSignature instance.
            dependency_names: A set of dependency names.
            type_overrides: A dictionary of type overrides, either will override a parameter type with a type derived
                from a plugin, or set the type to ``Any`` if validation should be skipped for the parameter.

        Returns:
            The created PydanticSignatureModel.
        """
        field_definitions: dict[str, tuple[Any, Any]] = {}

        for parameter in parsed_signature.parameters.values():
            field_type = type_overrides.get(parameter.name, parameter.annotation)

            if kwarg_definition := parameter.kwarg_definition:
                if isinstance(kwarg_definition, DependencyKwarg):
                    field_info = FieldInfo(
                        default=kwarg_definition.default if kwarg_definition.default is not Empty else None,
                        kwarg_definition=kwarg_definition,
                        field_definition=parameter,
                    )
                    if kwarg_definition.skip_validation:
                        field_type = Any
                else:
                    kwargs: dict[str, Any] = {k: v for k, v in asdict(kwarg_definition).items() if v is not Empty}

                    if "pattern" in kwargs:
                        kwargs["regex"] = kwargs["pattern"]

                    field_info = FieldInfo(
                        **kwargs,
                        kwarg_definition=kwarg_definition,
                        field_definition=parameter,
                    )
            else:
                field_info = FieldInfo(default=..., field_definition=parameter)

                if is_pydantic_constrained_field(parameter.default):
                    field_type = parameter.default
                elif parameter.has_default:
                    field_info.default = parameter.default
                elif parameter.is_optional:
                    field_info.default = None

            field_definitions[parameter.name] = (field_type, field_info)

        model: type[PydanticSignatureModel] = create_model(  # type: ignore
            f"{fn_name}_signature_model",
            __base__=PydanticSignatureModel,
            __module__=fn_module or "pydantic.main",
            **field_definitions,  # pyright: ignore
        )
        model.return_annotation = parsed_signature.return_type.annotation
        model.dependency_name_set = dependency_names
        model.populate_field_definitions()
        return model

    @classmethod
    def _get_error_messages(cls, e: ValidationError, connection: ASGIConnection) -> list[ErrorMessage]:
        """Get error messages from a ValidationError."""
        messages: list[ErrorMessage] = []

        for exc in e.errors():
            keys = [str(loc) for loc in exc["loc"]]
            message = super()._build_error_message(keys=keys, exc_msg=exc["msg"], connection=connection)
            messages.append(message)

        return messages
