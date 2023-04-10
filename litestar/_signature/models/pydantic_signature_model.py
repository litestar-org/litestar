from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from pydantic import BaseConfig, BaseModel, ValidationError, create_model
from pydantic.fields import FieldInfo, ModelField

from litestar._signature.field import SignatureField
from litestar._signature.models.base import SignatureModel
from litestar.constants import UNDEFINED_SENTINELS
from litestar.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from litestar.types import Empty
from litestar.utils.predicates import is_pydantic_constrained_field

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.plugins import PluginMapping
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
            raise cls._create_exception(
                messages=[{"key": str(exc["loc"][-1]), "message": exc["msg"]} for exc in e.errors()],
                connection=connection,
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

    @classmethod
    def create(
        cls,
        fn_name: str,
        fn_module: str | None,
        parsed_signature: ParsedSignature,
        field_plugin_mappings: dict[str, PluginMapping],
        dependency_names: set[str],
        type_overrides: dict[str, Any],
    ) -> type[PydanticSignatureModel]:
        """Create a pydantic based SignatureModel.

        Args:
            fn_name: Name of the callable.
            fn_module: Name of the function's module, if any.
            parsed_signature: A ParsedSignature instance.
            field_plugin_mappings: A mapping of field names to plugin mappings.
            dependency_names: A set of dependency names.
            type_overrides: A dictionary of type overrides, either will override a parameter type with a type derived
                from a plugin, or set the type to ``Any`` if validation should be skipped for the parameter.

        Returns:
            The created PydanticSignatureModel.
        """
        field_definitions: dict[str, tuple[Any, Any]] = {}

        for parameter in parsed_signature.parameters.values():
            field_type = type_overrides.get(parameter.name, parameter.parsed_type.annotation)

            if kwargs_container := parameter.kwarg_container:
                if isinstance(kwargs_container, DependencyKwarg):
                    field_info = FieldInfo(
                        default=kwargs_container.default if kwargs_container.default is not Empty else None,
                        kwargs_model=kwargs_container,
                        parsed_parameter=parameter,
                    )
                    if kwargs_container.skip_validation:
                        field_type = Any
                else:
                    field_info = FieldInfo(
                        **{k: v for k, v in asdict(kwargs_container).items() if v is not Empty},
                        kwargs_model=kwargs_container,
                        parsed_parameter=parameter,
                    )
            else:
                field_info = FieldInfo(default=..., parsed_parameter=parameter)

                if is_pydantic_constrained_field(parameter.default):
                    field_type = parameter.default
                elif parameter.has_default:
                    field_info.default = parameter.default
                elif parameter.parsed_type.is_optional:
                    field_info.default = None

            field_definitions[parameter.name] = (field_type, field_info)

        model: type[PydanticSignatureModel] = create_model(  # type: ignore
            f"{fn_name}_signature_model",
            __base__=PydanticSignatureModel,
            __module__=fn_module or "pydantic.main",
            **field_definitions,
        )
        model.return_annotation = parsed_signature.return_type.annotation
        model.field_plugin_mappings = field_plugin_mappings
        model.dependency_name_set = dependency_names
        model.populate_signature_fields()
        return model
