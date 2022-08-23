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

    from starlite.types import (
        AfterRequestHandler,
        AfterResponseHandler,
        BeforeRequestHandler,
        ControllerRouterHandler,
        Dependencies,
        ExceptionHandlersMap,
        Guard,
        LifeCycleHandler,
        Middleware,
        ParametersMap,
        ResponseCookies,
        ResponseHeadersMap,
        ResponseType,
    )

ModelT = TypeVar("ModelT")


@runtime_checkable
class PluginProtocol(Protocol[ModelT]):  # pragma: no cover
    def provide_route_handlers(self) -> List["ControllerRouterHandler"]:
        """Allows providing a list of route handlers (decorated functions,
        controllers and routers) to be registered on the app.

        Returns:
            A list of [Route Handler][starlite.types.ControllerRouterHandler].
        """
        return []

    def provide_on_startup_handlers(self, on_startup: List["LifeCycleHandler"]) -> List["LifeCycleHandler"]:
        """Receives the list of callables, sync or async, to execute on
        application startup and returns an updated list.

        Args:
            on_startup: A list of [Life Cycle Handlers][starlite.types.LifeCycleHandler].

        Returns:
            A list of [Life Cycle Handlers][starlite.types.LifeCycleHandler].
        """
        return on_startup

    def provide_on_shutdown_handlers(self, on_shutdown: List["LifeCycleHandler"]) -> List["LifeCycleHandler"]:
        """Receives the list of callables, sync or async, to execute on
        application shutdown and returns an updated list.

        Args:
            on_shutdown: A list of [Life Cycle Handlers][starlite.types.LifeCycleHandler].

        Returns:
            A list of [Life Cycle Handlers][starlite.types.LifeCycleHandler].
        """
        return on_shutdown

    def provide_after_request(self) -> Optional["AfterRequestHandler"]:
        """Allows providing an after request handler. If provided it will be
        set on the application level.

        Returns:
            An [After Request Handler][starlite.types.AfterRequestHandler].
        """
        return None

    def provide_before_request(self) -> Optional["BeforeRequestHandler"]:
        """Allows providing a before request handler. If provided it will be
        set on the application level.

        Returns:
            A [Before Request Handler][starlite.types.BeforeRequestHandler].
        """
        return None

    def provide_after_response(self) -> Optional["AfterResponseHandler"]:
        """Allows providing an after response handler. If provided it will be
        set on the application level.

        Returns:
            An [After Response Handler][starlite.types.AfterResponseHandler].
        """
        return None

    def provide_exception_handlers(self) -> "ExceptionHandlersMap":
        """Allows returning a mapping of exception handler functions.

        Returns:
            An [Exception Handler Mapping][starlite.types.ExceptionHandlersMap].
        """
        return {}

    def provide_guards(self) -> List["Guard"]:
        """Allows returning a list of route guard functions.

        Returns:
            A list of [Guard][starlite.types.Guard] callables.
        """
        return []

    def provide_middlewares(self, middlewares: List["Middleware"]) -> List["Middleware"]:
        """Receives the list of user provided middlewares and returns an
        updated list of middlewares. This is intended to allow the plugin to
        determine the order of insertion of middlewares.

        Args:
            middlewares: The list of user provided middlewares provided on the Starlite app constructor
                (i.e. app 'level' middlewares).
        Returns:
            An updates list of [Middlewares][starlite.types.Middleware].
        """
        return middlewares

    def provide_dependencies(self) -> "Dependencies":
        """Provides dependencies to the application. Any .

        Returns:
            A string keyed dictionary of dependency [Provider][starlite.provide.Provide] instances.
        """
        return {}

    def provide_parameters(self) -> "ParametersMap":
        """Allows providing a mapping of [Parameter][starlite.params.Parameter]
        definitions that will be available to all application paths.

        Returns:
            A [Mapping of Parameters][starlite.types.ParametersMap]
        """
        return {}

    def provide_response_class(self) -> Optional["ResponseType"]:
        """Allows providing a custom subclass of [starlite.response.Response]
        to be used as the default response for all route handlers under the
        controller.

        Returns:
            A [Custom Response Subclass][starlite.types.ResponseType]
        """
        return None

    def provide_response_headers(self) -> "ResponseHeadersMap":
        """Allows providing a string keyed dictionary mapping.

        [ResponseHeader][starlite.datastructures.ResponseHeader] instances.

        Returns:
            A [Response Header Mapping][starlite.types.ResponseHeadersMap]
        """
        return {}

    def provide_response_cookies(self) -> "ResponseCookies":
        """Allows providing a list of [Cookie](starlite.datastructures.Cookie]
        instances.

        Returns:
            A [List of Cookie instances][starlite.types.ResponseCookies]
        """
        return []

    def provide_openapi_tags(self) -> List[str]:
        """Allows providing a list of string tags that will be appended to the
        schema of all route handlers.

        Returns:
            A list of strings.
        """
        return []

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

    def from_dict(self, model_class: Type[ModelT], **kwargs: Dict[str, Any]) -> ModelT:
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
