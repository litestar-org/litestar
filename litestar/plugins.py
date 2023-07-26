from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator, Protocol, TypeVar, Union, cast, runtime_checkable

if TYPE_CHECKING:
    from click import Group

    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.config.app import AppConfig
    from litestar.dto import AbstractDTO
    from litestar.openapi.spec import Schema
    from litestar.typing import FieldDefinition

__all__ = (
    "SerializationPluginProtocol",
    "InitPluginProtocol",
    "OpenAPISchemaPluginProtocol",
    "PluginProtocol",
    "CLIPluginProtocol",
    "PluginRegistry",
)


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
class CLIPluginProtocol(Protocol):
    """Plugin protocol to extend the CLI."""

    def on_cli_init(self, cli: Group) -> None:
        """Called when the CLI is initialized.

        This can be used to extend or override existing commands.

        Args:
            cli: The root :class:`click.Group` of the Litestar CLI

        Examples:
            .. code-block:: python

                from litestar import Litestar
                from litestar.plugins import CLIPluginProtocol
                from click import Group


                class CLIPlugin(CLIPluginProtocol):
                    def on_cli_init(self, cli: Group) -> None:
                        @cli.command()
                        def is_debug_mode(app: Litestar):
                            print(app.debug)


                app = Litestar(plugins=[CLIPlugin()])
        """


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

    def create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO]:
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

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        """Given a type annotation, transform it into an OpenAPI schema class.

        Args:
            field_definition: An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
            schema_creator: An instance of the openapi SchemaCreator.

        Returns:
            An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
        """
        raise NotImplementedError()


PluginProtocol = Union[
    SerializationPluginProtocol,
    InitPluginProtocol,
    OpenAPISchemaPluginProtocol,
    CLIPluginProtocol,
]

PluginT = TypeVar("PluginT", bound=PluginProtocol)


class PluginRegistry:
    __slots__ = {
        "init": "Plugins that implement the InitPluginProtocol",
        "openapi": "Plugins that implement the OpenAPISchemaPluginProtocol",
        "serialization": "Plugins that implement the SerializationPluginProtocol",
        "cli": "Plugins that implement the CLIPluginProtocol",
        "_plugins_by_type": None,
        "_plugins": None,
        "_get_plugins_of_type": None,
    }

    def __init__(self, plugins: list[PluginProtocol]) -> None:
        self._plugins_by_type = {type(p): p for p in plugins}
        self._plugins = frozenset(plugins)
        self.init = tuple(p for p in plugins if isinstance(p, InitPluginProtocol))
        self.openapi = tuple(p for p in plugins if isinstance(p, OpenAPISchemaPluginProtocol))
        self.serialization = tuple(p for p in plugins if isinstance(p, SerializationPluginProtocol))
        self.cli = tuple(p for p in plugins if isinstance(p, CLIPluginProtocol))

    def get(self, type_: type[PluginT]) -> PluginT:
        """Return the registered plugin of ``type_``.

        This should be used with subclasses of the plugin protocols.
        """
        try:
            return cast(PluginT, self._plugins_by_type[type_])  # type: ignore[index]
        except KeyError as e:
            raise KeyError(f"No plugin of type {type_.__name__!r} registered") from e

    def __iter__(self) -> Iterator[PluginProtocol]:
        return iter(self._plugins)

    def __contains__(self, item: PluginProtocol) -> bool:
        return item in self._plugins
