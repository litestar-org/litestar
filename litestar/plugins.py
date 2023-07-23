from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, Union, runtime_checkable

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.config.app import AppConfig
    from litestar.dto.interface import DTOInterface
    from litestar.dto.types import ForType
    from litestar.openapi.spec import Schema
    from litestar.typing import FieldDefinition


__all__ = ("SerializationPluginProtocol", "InitPluginProtocol", "OpenAPISchemaPluginProtocol", "PluginProtocol")


T = TypeVar("T")


@runtime_checkable
class InitPluginProtocol(Protocol):
    """Protocol used to define plugins that affect the application's init process."""

    __slots__ = ()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Receive the :class:`AppConfig<.config.app.AppConfig>` instance after `on_app_init` hooks have been called.

        Examples:
            .. code-block: python
                from litestar import Litestar, get
                from litestar.di import Provide
                from litestar.plugins import InitPluginProtocol

                def get_name() -> str:
                    return "world"

                @get("/my-path")
                def my_route_handler(name: str) -> dict[str, str]:
                    return {"hello": name}

                class MyPlugin(InitPluginProtocol):
                    def on_app_init(self, app_config: AppConfig) -> AppConfig:
                        app_config.dependencies["name"] = Provide(get_name)
                        app_config.route_handlers.append(my_route_handler)
                        return app_config

                app = Litestar(plugins=[MyPlugin()])

        Args:
            app_config: The :class:`AppConfig <litestar.config.app.AppConfig>` instance.

        Returns:
            The app config object.
        """
        return app_config  # pragma: no cover


@runtime_checkable
class SerializationPluginProtocol(Protocol):
    """Protocol used to define a serialization plugin for DTOs."""

    __slots__ = ()

    def supports_type(self, field_definition: FieldDefinition) -> bool:
        """Given a value of indeterminate type, determine if this value is supported by the plugin.

        Args:
            field_definition: A parsed type.

        Returns:
            Whether the type is supported by the plugin.
        """
        raise NotImplementedError()

    def create_dto_for_type(self, field_definition: FieldDefinition) -> type[DTOInterface]:
        """Given a parsed type, create a DTO class.

        Args:
            field_definition: A parsed type.

        Returns:
            A DTO class.
        """
        raise NotImplementedError()


@runtime_checkable
class OpenAPISchemaPluginProtocol(Protocol):
    """Plugin to extend the support of OpenAPI schema generation for non-library types."""

    __slots__ = ()

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        """Given a value of indeterminate type, determine if this value is supported by the plugin.

        Args:
            value: An arbitrary value.

        Returns:
            A typeguard dictating whether the value is supported by the plugin.
        """
        raise NotImplementedError()

    def to_openapi_schema(self, annotation: Any, schema_creator: SchemaCreator, dto_for: ForType | None) -> Schema:
        """Given a type annotation, transform it into an OpenAPI schema class.

        Args:
            annotation: A type annotation.
            schema_creator: An instance of the openapi SchemaCreator.
            dto_for: The type of the DTO if any.

        Returns:
            An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
        """
        raise NotImplementedError()


PluginProtocol = Union[SerializationPluginProtocol, InitPluginProtocol, OpenAPISchemaPluginProtocol]
