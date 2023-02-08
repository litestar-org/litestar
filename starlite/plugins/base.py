from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)

from pydantic import BaseModel
from typing_extensions import TypeGuard, get_args

from starlite.types.protocols import DataclassProtocol

if TYPE_CHECKING:
    from pydantic_openapi_schema.v3_1_0 import Schema

    from starlite.app import Starlite

ModelT = TypeVar("ModelT")
DataContainerT = TypeVar("DataContainerT", bound=Union[BaseModel, DataclassProtocol, TypedDict])  # type: ignore[valid-type]


@runtime_checkable
class InitPluginProtocol(Protocol):
    """Protocol used to define plugins that affect the application's init process."""

    __slots__ = ()

    def on_app_init(self, app: "Starlite") -> None:
        """Receive the Starlite application instance before ``init`` is finalized and allow the plugin to update various
        attributes.

        Examples:
            .. code-block: python
                from starlite import Starlite, get
                from starlite.plugins import InitPluginProtocol


                @get("/my-path")
                def my_route_handler() -> dict[str, str]:
                    return {"hello": "world"}


                class MyPlugin(InitPluginProtocol):
                    def on_app_init(self, app: Starlite) -> None:
                        # update app attributes

                        app.after_request = ...
                        app.after_response = ...
                        app.before_request = ...
                        app.dependencies.update({...})
                        app.exception_handlers.update({...})
                        app.guards.extend(...)
                        app.middleware.extend(...)
                        app.on_shutdown.extend(...)
                        app.on_startup.extend(...)
                        app.parameters.update({...})
                        app.response_class = ...
                        app.response_cookies.extend(...)
                        app.response_headers.update(...)
                        app.tags.extend(...)

                        # register a route handler
                        app.register(my_route_handler)


        Args:
            app: The :class:`Starlite <starlite.app.Starlite>` instance.

        Returns:
            None
        """
        return None  # noqa: R501


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

    def to_dict(self, model_instance: ModelT) -> Union[Dict[str, Any], Awaitable[Dict[str, Any]]]:
        """Given an instance of a model supported by the plugin, return a dictionary of serializable values.

        Args:
            model_instance: A model instance of the type supported by the plugin.

        Notes:
            - This method can be async as well.

        Returns:
            A string keyed dictionary of values.
        """
        raise NotImplementedError()

    def from_dict(self, model_class: Type[ModelT], **kwargs: Any) -> ModelT:
        """Given a class supported by this plugin and a dict of values, create an instance of the class.

        Args:
            model_class: A model class supported by the plugin.
            **kwargs: A string keyed mapping of values.

        Returns:
            A model instance.
        """
        raise NotImplementedError()

    def to_data_container_class(self, model_class: Type[ModelT], **kwargs: Any) -> Type[DataContainerT]:
        """Create a data container class corresponding to the given model class.

        :param model_class: The model class that serves as a basis.
        :param kwargs: Any kwargs.
        :return: The generated data container class.
        """
        raise NotImplementedError()

    def from_data_container_instance(
        self, model_class: Type[ModelT], data_container_instance: DataContainerT
    ) -> ModelT:
        """Create a model instance from the given data container instance.

        :param model_class: The model class to be instantiated.
        :param data_container_instance: The data container instance.
        :return: A model instance.
        """
        raise NotImplementedError()


@runtime_checkable
class OpenAPISchemaPluginProtocol(Protocol[ModelT]):
    """Protocol used to defined plugins that extends the support of OpenAPI schema generation for non-library types."""

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

    def to_openapi_schema(self, model_class: Type[ModelT]) -> "Schema":
        """Given a model class, transform it into an OpenAPI schema class.

        :param model_class: A model class.
        :return: An :class:`OpenAPI <pydantic_openapi_schema.v3_1_0.schema.Schema>` instance.
        """
        raise NotImplementedError()


def get_plugin_for_value(
    value: Any, plugins: List[SerializationPluginProtocol]
) -> Optional[SerializationPluginProtocol]:
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
        if get_args(value):
            value = get_args(value)[0]
        for plugin in plugins:
            if plugin.is_plugin_supported_type(value):
                return plugin
    return None


class PluginMapping(NamedTuple):
    """Named tuple, mapping plugins > models."""

    plugin: SerializationPluginProtocol[Any, Any]
    model_class: Any

    def get_model_instance_for_value(
        self, value: Union[DataContainerT, List[DataContainerT], Tuple[DataContainerT, ...]]
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
