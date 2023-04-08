from __future__ import annotations

from collections.abc import Iterable
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    NamedTuple,
    Protocol,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)

from pydantic import BaseModel
from typing_extensions import TypeGuard, get_args

from litestar.types.protocols import DataclassProtocol
from litestar.utils.predicates import is_class_and_subclass

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.openapi.spec import Schema

__all__ = (
    "InitPluginProtocol",
    "OpenAPISchemaPluginProtocol",
    "PluginMapping",
    "PluginProtocol",
    "SerializationPluginProtocol",
    "get_plugin_for_value",
)

ModelT = TypeVar("ModelT")
DataContainerT = TypeVar("DataContainerT", bound=Union[BaseModel, DataclassProtocol, TypedDict])  # type: ignore[valid-type]


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
class SerializationPluginProtocol(Protocol[ModelT, DataContainerT]):
    """Protocol used to define a serialization plugin.
    Serialization plugins are used to extend serialization and deserialization support.
    """

    __slots__ = ()

    @staticmethod
    def is_plugin_supported_type(value: Any) -> TypeGuard[ModelT]:
        """Given a value of indeterminate type, determine if this value is supported by the plugin.

        Args:
            value: An arbitrary value.

        Returns:
            A typeguard dictating whether the value is supported by the plugin.
        """
        raise NotImplementedError()

    def to_dict(self, model_instance: ModelT) -> dict[str, Any] | Awaitable[dict[str, Any]]:
        """Given an instance of a model supported by the plugin, return a dictionary of serializable values.

        Args:
            model_instance: A model instance of the type supported by the plugin.

        Notes:
            - This method can be async as well.

        Returns:
            A string keyed dictionary of values.
        """
        raise NotImplementedError()

    def from_dict(self, model_class: type[ModelT], **kwargs: Any) -> ModelT:
        """Given a class supported by this plugin and a dict of values, create an instance of the class.

        Args:
            model_class: A model class supported by the plugin.
            **kwargs: A string keyed mapping of values.

        Returns:
            A model instance.
        """
        raise NotImplementedError()

    def to_data_container_class(self, model_class: type[ModelT], **kwargs: Any) -> type[DataContainerT]:
        """Create a data container class corresponding to the given model class.

        Args:
            model_class: The model class that serves as a basis.
            **kwargs: Any kwargs.

        Returns:
            The generated data container class.
        """
        raise NotImplementedError()

    def from_data_container_instance(
        self, model_class: type[ModelT], data_container_instance: DataContainerT
    ) -> ModelT:
        """Create a model instance from the given data container instance.

        Args:
            model_class: The model class to be instantiated.
            data_container_instance: The data container instance.

        Returns:
            A model instance.
        """
        raise NotImplementedError()


@runtime_checkable
class OpenAPISchemaPluginProtocol(Protocol[ModelT]):
    """Plugin to extend the support of OpenAPI schema generation for non-library types."""

    __slots__ = ()

    @staticmethod
    def is_plugin_supported_type(value: Any) -> TypeGuard[ModelT]:
        """Given a value of indeterminate type, determine if this value is supported by the plugin.

        Args:
            value: An arbitrary value.

        Returns:
            A typeguard dictating whether the value is supported by the plugin.
        """
        raise NotImplementedError()

    def to_openapi_schema(self, model_class: type[ModelT]) -> "Schema":
        """Given a model class, transform it into an OpenAPI schema class.

        Args:
            model_class: A model class.

        Returns:
            An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
        """
        raise NotImplementedError()


def get_plugin_for_value(value: Any, plugins: list[SerializationPluginProtocol]) -> SerializationPluginProtocol | None:
    """Return a plugin for handling the given value, if any plugin supports it.

    Args:
        value: An arbitrary value.
        plugins: A list of plugins

    Returns:
        A plugin supporting the given value, or ``None``.
    """
    if plugins:
        if value and isinstance(value, (list, tuple)):
            value = value[0]
        if is_class_and_subclass(value, Iterable) and (args := get_args(value)):  # type:ignore[type-abstract]
            value = args[0]
        for plugin in plugins:
            if plugin.is_plugin_supported_type(value):
                return plugin
    return None


class PluginMapping(NamedTuple):
    """Named tuple, mapping plugins > models."""

    plugin: SerializationPluginProtocol[Any, Any]
    model_class: Any

    def get_model_instance_for_value(
        self, value: DataContainerT | list[DataContainerT] | tuple[DataContainerT, ...]
    ) -> Any:
        """Given a value generated by plugin, return an instance of the original class.

        Can also accept a list or tuple of values.

        Args:
            value: A pydantic model instance or sequence of instances.

        Returns:
            Any
        """
        if isinstance(value, (list, tuple)):
            return [self.plugin.from_data_container_instance(self.model_class, item) for item in value]
        return self.plugin.from_data_container_instance(self.model_class, value)


PluginProtocol = Union[SerializationPluginProtocol, InitPluginProtocol, OpenAPISchemaPluginProtocol]
