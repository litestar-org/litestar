from functools import partial
from inspect import Signature, getfullargspec, isclass, ismethod
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union, cast

from pydantic import (
    BaseConfig,
    BaseModel,
    Extra,
    Field,
    create_model,
    validate_arguments,
    validator,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route as StarletteRoute
from starlette.routing import Router as StarletteRouter
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from starlette.types import ASGIApp
from typing_extensions import AsyncContextManager, Literal, Type

from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.request import handle_request
from starlite.utils.sequence import find_index, unique
from starlite.utils.url import join_paths, normalize_path


class SignatureWrapper:
    fn: Optional[Callable] = None

    def get_signature_model(self) -> Type[BaseModel]:
        """
        Creates a pydantic model for the signature of a given function
        """
        if not self.fn:
            raise ValueError("get_signature_model can only be called once self.fn is set")

        class Config(BaseConfig):
            arbitrary_types_allowed = True

        try:
            signature = Signature.from_callable(self.fn)
            field_definitions: Dict[str, Tuple[Any, Any]] = {}

            for key, value in getfullargspec(self.fn).annotations.items():
                parameter = signature.parameters[key]
                if parameter.default is not signature.empty:
                    field_definitions[key] = (value, parameter.default)
                elif not repr(parameter.annotation).startswith("typing.Optional"):
                    field_definitions[key] = (value, ...)
                else:
                    field_definitions[key] = (value, None)
            return create_model(self.fn.__name__ + "SignatureModel", __config__=Config, **field_definitions)
        except (TypeError, ValueError) as e:
            raise ImproperlyConfiguredException("Unsupported callable passed to Inject") from e


class Inject(SignatureWrapper):
    def __init__(self, dependency: Callable):
        self.fn = dependency
        if ismethod(dependency) and hasattr(dependency, "__self__"):
            # ensure that the method's self argument is preserved
            self.fn = partial(dependency, dependency.__self__)  # type: ignore
        # TODO: re-add caching logic

    def __call__(self, **kwargs) -> Any:
        """
        Proxies call to 'self.proxy'
        """
        if not self.fn:
            raise ValueError()
        return self.fn(**kwargs)


class RouteHandler(SignatureWrapper, BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.allow

    http_method: Union[HttpMethod, List[HttpMethod]]
    status_code: Optional[int] = None
    include_in_schema: Optional[bool] = None
    media_type: Optional[MediaType] = None
    name: Optional[str] = None
    path: Optional[str] = None
    response_class: Optional[Type[Response]] = None
    response_headers: Optional[Union[dict, BaseModel]] = None
    dependencies: Optional[Dict[str, Inject]] = None

    fn: Optional[Callable] = None
    owner: Optional[Union[Type["Controller"], "Router"]] = None

    def __set_name__(self, owner: Optional[Type["Controller"]], *args):
        """
        __set_name__ is a hook that is called when a class is initialised,
        hence we are able to store the method's self argument as a field value
        """
        self.owner = owner

    def __call__(self, *args, **kwargs) -> Any:
        """
        If wrapper is None, set fn from args[0], otherwise, call fn and pass the *args and **kwargs to it
        """
        if self.fn:
            if self.owner:
                return self.fn(self.owner, *args, **kwargs)
            return self.fn(*args, **kwargs)

        self.fn = cast(Callable, args[0])
        return self

    def __eq__(self, other: Any) -> bool:
        try:
            return super().__eq__(other) and self.fn == other.fn
        except (AttributeError, ValueError):
            return False

    @validator("http_method", always=True, pre=True)
    def validate_http_method(  # pylint: disable=no-self-argument,no-self-use
        cls, value: Union[HttpMethod, List[HttpMethod]]
    ) -> Union[HttpMethod, List[HttpMethod]]:
        """Validates that a given value is an HttpMethod enum member or list thereof"""
        if isinstance(value, list):
            if len(value) == 1:
                value = value[0]
            elif value == 0:
                raise ValueError("An http_method parameter is required")
        return value

    @validator("status_code", always=True)
    def validate_status_code(  # pylint: disable=no-self-argument,no-self-use
        cls, value: Optional[int], values: Dict[str, Any]
    ) -> int:
        """
        Validates that status code is set for lists of 2 or more HttpMethods,
        and sets default for other cases where the status_code is not set.
        """
        if value:
            return value

        http_method = values["http_method"]
        if isinstance(http_method, list):
            raise ValueError("When defining multiple methods for a given path, a status_code is required")
        if http_method == HttpMethod.POST:
            return HTTP_201_CREATED
        if http_method == HttpMethod.DELETE:
            return HTTP_204_NO_CONTENT
        return HTTP_200_OK

    @validator("response_class")
    def validate_response_class(  # pylint: disable=no-self-argument,no-self-use
        cls, value: Any
    ) -> Optional[Type[Response]]:
        """
        Valides that value is either None or subclass of Starlette Response
        """
        if value is None or issubclass(value, Response):
            return value
        raise ValueError("response_class must be a sub-class of starlette.responses.Response")

    @property
    def http_methods(self) -> List[HttpMethod]:
        """
        Returns a list of the RouteHandler's HttpMethod members
        """
        return self.http_method if isinstance(self.http_method, list) else [self.http_method]

    @property
    def resolved_dependencies(self) -> Dict[str, Inject]:
        """
        Returns all dependencies that exist in the given handler's scopes
        """
        dependencies_list: List[Dict[str, Inject]] = []
        if self.dependencies:
            dependencies_list.append(self.dependencies)
        cur = self.owner
        while cur is not None:
            if cur.dependencies:
                dependencies_list.append(cur.dependencies)
            cur = cur.owner
        resolved_dependencies: Dict[str, Inject] = {}
        for dependencies_dict in reversed(dependencies_list):
            resolved_dependencies = {**resolved_dependencies, **dependencies_dict}
        return resolved_dependencies


route = RouteHandler


class get(RouteHandler):
    http_method: Literal[HttpMethod.GET] = Field(default=HttpMethod.GET)


class post(RouteHandler):
    http_method: Literal[HttpMethod.POST] = Field(default=HttpMethod.POST)


class put(RouteHandler):
    http_method: Literal[HttpMethod.PUT] = Field(default=HttpMethod.PUT)


class patch(RouteHandler):
    http_method: Literal[HttpMethod.PATCH] = Field(default=HttpMethod.PATCH)


class delete(route):
    http_method: Literal[HttpMethod.DELETE] = Field(default=HttpMethod.DELETE)


class Controller:
    path: str
    dependencies: Optional[Dict[str, Inject]] = None
    owner: "Router" = None  # type: ignore[assignment]

    def __init__(self, owner: "Router"):
        if not hasattr(self, "path") or not self.path:
            raise ImproperlyConfiguredException("Controller subclasses must set a path attribute")
        self.path = normalize_path(self.path)
        self.owner = owner

    def get_route_handlers(self) -> List[RouteHandler]:
        """
        Returns a list of route handlers defined on the controller
        """
        return [
            getattr(self, f_name)
            for f_name in dir(self)
            if f_name not in dir(Controller) and isinstance(getattr(self, f_name), RouteHandler)
        ]


class Route(StarletteRoute):
    route_handler_map: Dict[HttpMethod, RouteHandler]

    @validate_arguments()
    def __init__(
        self,
        *,
        path: str,
        route_handlers: Union[RouteHandler, Sequence[RouteHandler]],
    ):
        self.route_handler_map = {}
        name: Optional[str] = None
        include_in_schema = True

        for route_handler in route_handlers if isinstance(route_handlers, list) else [route_handlers]:
            for http_method in route_handler.http_methods:
                if self.route_handler_map.get(http_method):
                    raise ImproperlyConfiguredException(
                        f"handler already registered for path {path!r} and http method {http_method}"
                    )
                self.route_handler_map[http_method] = route_handler
                if route_handler.name:
                    name = route_handler.name
                if route_handler.include_in_schema is not None:
                    include_in_schema = route_handler.include_in_schema

        super().__init__(
            path=path,
            endpoint=self.create_endpoint_handler(self.route_handler_map),
            name=name,
            include_in_schema=include_in_schema,
            methods=[method.upper() for method in self.route_handler_map],
        )

    @staticmethod
    def create_endpoint_handler(http_handler_mapping: Dict[HttpMethod, RouteHandler]) -> Callable:
        """
        Create a Starlette endpoint handler given a dictionary mapping of http-methods to RouteHandlers

        Using this method, Starlite is able to support different handler functions for the same path.
        """

        async def endpoint_handler(request: Request) -> Response:
            request_method = HttpMethod.from_str(request.method)
            handler = http_handler_mapping[request_method]
            return await handle_request(route_handler=handler, request=request)

        return endpoint_handler


# noinspection PyMethodOverriding
class Router(StarletteRouter):
    routes: List[Route]
    owner: Optional["Router"] = None

    def __init__(
        self,
        path: str,
        route_handlers: Optional[Sequence[Union[Type[Controller], RouteHandler, "Router", Callable]]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        on_startup: Optional[Sequence[Callable]] = None,
        on_shutdown: Optional[Sequence[Callable]] = None,
        lifespan: Optional[Callable[[Any], AsyncContextManager]] = None,
        dependencies: Optional[Dict[str, Inject]] = None,
    ):
        if on_startup or on_shutdown:
            assert not lifespan, "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."
        self.path = normalize_path(path)
        self.dependencies = dependencies
        super().__init__(
            default=default,
            lifespan=lifespan,
            on_shutdown=on_shutdown,
            on_startup=on_startup,
            redirect_slashes=redirect_slashes,
            routes=[],
        )
        for route_handler in route_handlers or []:
            self.register(value=cast(Union[Type[Controller], RouteHandler, "Router"], route_handler))

    @property
    def route_handler_method_map(self) -> Dict[str, Dict[HttpMethod, RouteHandler]]:
        """
        Returns dictionary that maps paths (keys) to a list of route handler functions (values)
        """
        r_map: Dict[str, Dict[HttpMethod, RouteHandler]] = {}
        for r in self.routes:
            if not r_map.get(r.path):
                r_map[r.path] = {}
            for method, handler in r.route_handler_map.items():
                r_map[r.path][method] = handler
        return r_map

    @staticmethod
    def create_handler_http_method_map(
        value: Union[Controller, RouteHandler, "Router"],
    ) -> Dict[str, Dict[HttpMethod, RouteHandler]]:
        """
        Maps route handlers to http methods
        """
        handlers_map: Dict[str, Dict[HttpMethod, RouteHandler]] = {}
        if isinstance(value, RouteHandler):
            handlers_map[value.path or ""] = {http_method: value for http_method in value.http_methods}
        elif isinstance(value, Router):
            handlers_map = value.route_handler_method_map
        else:
            # we reassign the variable to give it a clearer meaning
            for route_handler in value.get_route_handlers():
                controller = cast(Controller, value)
                path = join_paths([controller.path, route_handler.path]) if route_handler.path else controller.path
                if not handlers_map.get(path):
                    handlers_map[path] = {}
                for http_method in route_handler.http_methods:
                    handlers_map[path][http_method] = route_handler
        return handlers_map

    def validate_registration_value(
        self, value: Union[Type[Controller], RouteHandler, "Router"]
    ) -> Union[Controller, RouteHandler, "Router"]:
        """
        Validates that the value passed to the register method is supported
        """
        if isclass(value) and issubclass(value, Controller):
            return value(owner=self)
        if not isinstance(value, (Router, RouteHandler)):
            raise ImproperlyConfiguredException(
                "Unsupported value passed to `Router.register`. "
                "If you passed in a function or method, "
                "make sure to decorate it first with one of the routing decorators"
            )
        if isinstance(value, Router):
            if value.owner:
                raise ImproperlyConfiguredException(f"Router with path {value.path} has already been registered")
            if value == self:
                raise ImproperlyConfiguredException("Cannot register a router on itself")
        return cast(Union[Controller, RouteHandler, "Router"], value)

    def register(self, value: Union[Type[Controller], RouteHandler, "Router"]):
        """
        Register a Controller, Route instance or RouteHandler on the router

        Accepts a subclass or instance of Controller, an instance of Router or a function/method that has been decorated
        by any of the routing decorators (e.g. route, get, post...) exported from 'starlite.routing'
        """
        validated_value = self.validate_registration_value(value)
        if not validated_value.owner:
            validated_value.owner = self
        handlers_map = self.create_handler_http_method_map(value=validated_value)

        for route_path, method_map in handlers_map.items():
            path = join_paths([self.path, route_path])
            route_handlers = unique(method_map.values())
            if self.route_handler_method_map.get(path):
                existing_route_index = find_index(self.routes, "path", path)
                assert existing_route_index != -1, "unable to find_index existing route index"
                self.routes[existing_route_index] = Route(
                    path=path,
                    route_handlers=unique([*list(self.route_handler_method_map[path].values()), *route_handlers]),
                )
            else:
                self.routes.append(Route(path=path, route_handlers=route_handlers))

    def route(  # pylint: disable=arguments-differ
        self,
        path: str,
        http_method: Union[HttpMethod, List[HttpMethod]],
        include_in_schema: Optional[bool] = None,
        media_type: Optional[MediaType] = None,
        name: Optional[str] = None,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Union[dict, BaseModel]] = None,
        status_code: Optional[int] = None,
    ) -> Callable:
        """
        Decorator that creates a route, similarly to the route decorator exported from 'starlite.routing',
        and then registers it on the given router.
        """

        def inner(fn: Callable) -> RouteHandler:
            route_handler = RouteHandler(
                http_method=http_method,
                include_in_schema=include_in_schema,
                media_type=media_type,
                name=name,
                path=path,
                response_class=response_class,
                response_headers=response_headers,
                status_code=status_code,
                fn=fn,
            )
            self.register(value=route_handler)
            return route_handler

        return inner

    def add_route(  # pylint: disable=arguments-differ
        self,
        path: str,
        endpoint: Callable,
        http_method: Union[HttpMethod, List[HttpMethod]],
        include_in_schema: Optional[bool] = None,
        media_type: Optional[MediaType] = None,
        name: Optional[str] = None,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Union[dict, BaseModel]] = None,
        status_code: Optional[int] = None,
    ) -> None:
        """
        Creates a route handler function using router.route(**kwargs), and then registers it on the given router.
        """
        route_handler = RouteHandler(
            http_method=http_method,
            include_in_schema=include_in_schema,
            media_type=media_type,
            name=name,
            path=path,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            fn=endpoint,
        )
        self.register(value=route_handler)
