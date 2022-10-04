from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import Protocol, TypeGuard, get_args, runtime_checkable

if TYPE_CHECKING:
    from pydantic import BaseModel

    from starlite.app import Starlite

ModelT = TypeVar("ModelT")


@runtime_checkable
class PluginProtocol(Protocol[ModelT]):  # pragma: no cover
    __slots__ = ()

    def on_app_init(self, app: "Starlite") -> None:
        """Receives the Starlite application instance before `init` is
        finalized and allows the plugin to update various attributes.

        Examples:
            ```python
            from starlite import PluginProtocol, Starlite, get


            @get("/my-path")
            def my_route_handler() -> dict[str, str]:
                return {"hello": "world"}


            class MyPlugin(PluginProtocol[Any]):
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
            ```

        Args:
            app: The [Starlite][starlite.app.Starlite] instance.

        Returns:
            None
        """
        return None

    @staticmethod
    def is_plugin_supported_type(value: Any) -> TypeGuard[ModelT]:
        """Given a value of indeterminate type, determine if this value is
        supported by the plugin.

        Args:
            value: An arbitrary value.

        Returns:
            A typeguard dictating whether the value is supported by the plugin.
        """
        return False

    def to_pydantic_model_class(self, model_class: Type[ModelT], **kwargs: Any) -> Type["BaseModel"]:
        """Given a model_class supported by the plugin, convert it to a
        subclass of the pydantic BaseModel.

        Args:
            model_class: A model class supported by the plugin.
            **kwargs: Any additional kwargs.

        Returns:
            A pydantic model class.
        """
        raise NotImplementedError()

    def from_pydantic_model_instance(self, model_class: Type[ModelT], pydantic_model_instance: "BaseModel") -> ModelT:
        """Given an instance of a pydantic model created using a plugin's
        'to_pydantic_model_class', return an instance of the class from which
        that pydantic model has been created.

        This class is passed in as the 'model_class' kwarg.

        Args:
            model_class: A model class supported by the plugin.
            pydantic_model_instance: A pydantic model instance.

        Returns:
            A model instance.
        """
        raise NotImplementedError()

    def to_dict(self, model_instance: ModelT) -> Union[Dict[str, Any], Awaitable[Dict[str, Any]]]:
        """Given an instance of a model supported by the plugin, return a
        dictionary of serializable values.

        Args:
            model_instance: A model instance of the type supported by the plugin.

        Notes:
            - This method can be async as well.

        Returns:
            A string keyed dictionary of values.
        """
        raise NotImplementedError()

    def from_dict(self, model_class: Type[ModelT], **kwargs: Any) -> ModelT:
        """Given a class supported by this plugin and a dict of values, create
        an instance of the class.

        Args:
            model_class: A model class supported by the plugin.
            **kwargs: A string keyed mapping of values.

        Returns:
            A model instance.
        """
        raise NotImplementedError()


def get_plugin_for_value(value: Any, plugins: List[PluginProtocol]) -> Optional[PluginProtocol]:
    """Helper function to return a plugin for handling the given value, if any
    plugin supports it.

    Args:
        value: An arbitrary value.
        plugins: A list of plugins

    Returns:
        A plugin supporting the given value, or 'None'.
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
    plugin: PluginProtocol
    model_class: Any

    def get_model_instance_for_value(
        self, value: Union["BaseModel", List["BaseModel"], Tuple["BaseModel", ...]]
    ) -> Any:
        """Given a value generated by plugin, return an instance of the
        original class.

        Can also accept a list or tuple of values.

        Args:
            value: A pydantic model instance or sequence of instances.

        Returns:
            Any
        """
        if isinstance(value, (list, tuple)):
            return [
                self.plugin.from_pydantic_model_instance(self.model_class, pydantic_model_instance=item)
                for item in value
            ]
        return self.plugin.from_pydantic_model_instance(self.model_class, pydantic_model_instance=value)
