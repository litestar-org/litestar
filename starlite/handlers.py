from contextlib import suppress
from enum import Enum
from inspect import Signature, isawaitable, isclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from pydantic import BaseModel, Extra, Field, ValidationError, validator
from pydantic.error_wrappers import display_errors
from pydantic.typing import AnyCallable
from starlette.requests import HTTPConnection
from starlette.responses import FileResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from typing_extensions import Literal

from starlite.constants import REDIRECT_STATUS_CODES
from starlite.controller import Controller
from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import (
    HTTPException,
    ImproperlyConfiguredException,
    ValidationException,
)
from starlite.plugins.base import PluginMapping, get_plugin_for_value
from starlite.provide import Provide
from starlite.request import Request, WebSocket, get_model_kwargs_from_connection
from starlite.response import Response
from starlite.types import File, Guard, Redirect, ResponseHeader, Stream
from starlite.utils import SignatureModel

if TYPE_CHECKING:  # pragma: no cover
    from starlite.routing import Router


class _empty:
    """Placeholder"""


def get_signature_model(value: Any) -> Type[SignatureModel]:
    """
    Helper function to retrieve and validate the signature model from a provider or handler
    """
    try:
        return cast(Type[SignatureModel], getattr(value, "signature_model"))
    except AttributeError as e:  # pragma: no cover
        raise ImproperlyConfiguredException(f"The 'signature_model' attribute for {value} is not set") from e


class BaseRouteHandler(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.allow

    dependencies: Optional[Dict[str, Provide]] = None
    guards: Optional[List[Guard]] = None
    path: Optional[str] = None
    opt: Dict[str, Any] = {}

    fn: Optional[AnyCallable] = None
    owner: Optional[Union[Controller, "Router"]] = None
    resolved_dependencies: Union[Dict[str, Provide], Type[_empty]] = _empty
    resolved_guards: Union[List[Guard], Type[_empty]] = _empty
    signature_model: Optional[Type[SignatureModel]] = None

    def resolve_guards(self) -> List[Guard]:
        """Returns all guards in the handlers scope, starting from highest to current layer"""
        if self.resolved_guards is _empty:
            resolved_guards: List[Guard] = []
            cur: Any = self
            while cur is not None:
                if cur.guards:
                    resolved_guards.extend(cur.guards)
                cur = cur.owner
            # we reverse the list to ensure that the highest level guards are called first
            self.resolved_guards = list(reversed(resolved_guards))
        return cast(List[Guard], self.resolved_guards)

    def resolve_dependencies(self) -> Dict[str, Provide]:
        """
        Returns all dependencies correlating to handler function's kwargs that exist in the handler's scope
        """
        if not self.signature_model:
            raise RuntimeError("resolve_dependencies cannot be called before a signature model has been generated")
        if self.resolved_dependencies is _empty:
            field_names = list(self.signature_model.__fields__.keys())
            dependencies: Dict[str, Provide] = {}
            cur: Any = self
            while cur is not None:
                for key, value in (cur.dependencies or {}).items():
                    self.validate_dependency_is_unique(dependencies=dependencies, key=key, provider=value)
                    if key in field_names and key not in dependencies:
                        dependencies[key] = value
                cur = cur.owner
            self.resolved_dependencies = dependencies
        return cast(Dict[str, Provide], self.resolved_dependencies)

    @staticmethod
    def validate_dependency_is_unique(dependencies: Dict[str, Provide], key: str, provider: Provide) -> None:
        """
        Validates that a given provider has not been already defined under a different key
        """
        for dependency_key, value in dependencies.items():
            if provider == value:
                raise ImproperlyConfiguredException(
                    f"Provider for key {key} is already defined under the different key {dependency_key}. "
                    f"If you wish to override a provider, it must have the same key."
                )

    def validate_handler_function(self) -> None:
        """
        Validates the route handler function once it's set by inspecting its return annotations
        """
        if not self.fn:
            raise ImproperlyConfiguredException("cannot call validate_handler_function without first setting self.fn")

    async def authorize_connection(self, connection: HTTPConnection) -> None:
        """
        Ensures the connection is authorized by running all the route guards in scope
        """
        for guard in self.resolve_guards():
            result = guard(connection, self.copy())
            if isawaitable(result):
                await result

    async def get_parameters_from_connection(self, connection: HTTPConnection) -> Dict[str, Any]:
        """
        Parse the signature_model of the route handler return values matching function parameter keys as well as dependencies
        """
        signature_model = get_signature_model(self)
        try:
            # dependency injection
            dependencies: Dict[str, Any] = {}
            for key, provider in self.resolve_dependencies().items():
                provider_signature_model = get_signature_model(provider)
                provider_kwargs = await get_model_kwargs_from_connection(
                    connection=connection, fields=provider_signature_model.__fields__
                )
                value = provider(**provider_signature_model(**provider_kwargs).dict())
                if isawaitable(value):
                    value = await value
                dependencies[key] = value
            model_kwargs = await get_model_kwargs_from_connection(
                connection=connection,
                fields={k: v for k, v in signature_model.__fields__.items() if k not in dependencies},
            )
            # we return the model's attributes as a dict in order to preserve any nested models
            fields = list(signature_model.__fields__.keys())

            output: Dict[str, Any] = {}
            modelled_signature = signature_model(**model_kwargs, **dependencies)
            for key in fields:
                value = modelled_signature.__getattribute__(key)
                plugin_mapping: Optional[PluginMapping] = signature_model.field_plugin_mappings.get(key)
                if plugin_mapping:
                    if isinstance(value, (list, tuple)):
                        output[key] = [
                            plugin_mapping.plugin.from_pydantic_model_instance(
                                plugin_mapping.model_class, pydantic_model_instance=v
                            )
                            for v in value
                        ]
                    else:
                        output[key] = plugin_mapping.plugin.from_pydantic_model_instance(
                            plugin_mapping.model_class, pydantic_model_instance=value
                        )
                else:
                    output[key] = value
            return output
        except ValidationError as e:
            raise ValidationException(
                detail=f"Validation failed for {connection.method if isinstance(connection, Request) else 'websocket'} {connection.url}:\n\n{display_errors(e.errors())}"
            ) from e


class HTTPRouteHandler(BaseRouteHandler):
    http_method: Union[HttpMethod, List[HttpMethod]]
    media_type: Union[MediaType, str] = MediaType.JSON
    response_class: Optional[Type[Response]] = None
    response_headers: Optional[Dict[str, ResponseHeader]] = None
    status_code: Optional[int] = None

    resolved_headers: Union[Dict[str, ResponseHeader], Type[_empty]] = _empty
    resolved_response_class: Union[Type[Response], Type[_empty]] = _empty

    # OpenAPI related attributes
    include_in_schema: bool = True
    content_encoding: Optional[str] = None
    content_media_type: Optional[str] = None
    deprecated: bool = False
    description: Optional[str] = None
    operation_id: Optional[str] = None
    raises: Optional[List[Type[HTTPException]]] = None
    response_description: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None

    def __call__(self, fn: AnyCallable) -> "HTTPRouteHandler":
        """
        Replaces a function with itself
        """
        self.fn = fn
        self.validate_handler_function()
        return self

    def resolve_response_class(self) -> Type[Response]:
        """Return the closest custom Response class in the owner graph or the default Response class"""
        if self.resolved_response_class is _empty:
            self.resolved_response_class = Response
            cur: Any = self
            while cur is not None:
                if cur.response_class is not None:
                    self.resolved_response_class = cast(Type[Response], cur.response_class)
                    break
                cur = cur.owner
        return cast(Type[Response], self.resolved_response_class)

    def resolve_response_headers(self) -> Dict[str, ResponseHeader]:
        """
        Returns all header parameters in the scope of the handler function
        """
        if self.resolved_headers is _empty:
            headers: Dict[str, ResponseHeader] = {}
            cur: Any = self
            while cur is not None:
                for key, value in (cur.response_headers or {}).items():
                    if key not in headers:
                        headers[key] = value
                cur = cur.owner
            self.resolved_headers = headers
        return cast(Dict[str, ResponseHeader], self.resolved_headers)

    @validator("http_method", always=True, pre=True)
    def validate_http_method(  # pylint: disable=no-self-argument,no-self-use
        cls, value: Union[HttpMethod, List[HttpMethod]]
    ) -> Union[HttpMethod, List[HttpMethod]]:
        """Validates that a given value is an HttpMethod enum member or list thereof"""
        if not value:
            raise ValueError("An http_method parameter is required")
        if isinstance(value, list):
            value = [HttpMethod.from_str(v) for v in value]
            if len(value) == 1:
                value = value[0]
        else:
            value = HttpMethod.from_str(value)
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

        http_method = values.get("http_method")
        if not http_method:
            raise ValueError("http_method is not set")
        if isinstance(http_method, list):
            raise ValueError("When defining multiple methods for a given path, a status_code is required")
        if http_method == HttpMethod.POST:
            return HTTP_201_CREATED
        if http_method == HttpMethod.DELETE:
            return HTTP_204_NO_CONTENT
        return HTTP_200_OK

    @property
    def http_methods(self) -> List[HttpMethod]:
        """
        Returns a list of the RouteHandler's HttpMethod members
        """
        return self.http_method if isinstance(self.http_method, list) else [self.http_method]

    def validate_handler_function(self) -> None:
        """
        Validates the route handler function once it is set by inspecting its return annotations
        """
        super().validate_handler_function()
        return_annotation = Signature.from_callable(cast(AnyCallable, self.fn)).return_annotation
        if return_annotation is Signature.empty:
            raise ValidationException(
                "A return value of a route handler function should be type annotated."
                "If your function doesn't return a value or returns None, annotate it as returning None."
            )
        if isclass(return_annotation):
            with suppress(TypeError):
                if issubclass(return_annotation, Redirect) and self.status_code not in REDIRECT_STATUS_CODES:
                    raise ValidationException(
                        f"Redirect responses should have one of "
                        f"the following status codes: {', '.join([str(s) for s in REDIRECT_STATUS_CODES])}"
                    )
                if issubclass(return_annotation, File) and self.media_type in [MediaType.JSON, MediaType.HTML]:
                    self.media_type = MediaType.TEXT

    async def handle_request(self, request: Request) -> StarletteResponse:
        """
        Handles a given Request in relation to self.
        """
        if not self.fn:
            raise ImproperlyConfiguredException("cannot call a route handler without a decorated function")
        await self.authorize_connection(connection=request)
        params = await self.get_parameters_from_connection(connection=request)

        if isinstance(self.owner, Controller):
            data = self.fn(self.owner, **params)
        else:
            data = self.fn(**params)
        if isawaitable(data):
            data = await data
        if isinstance(data, StarletteResponse):
            return data

        status_code = cast(int, self.status_code)
        headers = {k: v.value for k, v in self.resolve_response_headers().items()}
        if isinstance(data, Redirect):
            return RedirectResponse(headers=headers, status_code=status_code, url=data.path)

        media_type = self.media_type.value if isinstance(self.media_type, Enum) else self.media_type
        if isinstance(data, File):
            return FileResponse(media_type=media_type, headers=headers, **data.dict())
        if isinstance(data, Stream):
            return StreamingResponse(
                content=data.iterator, status_code=status_code, media_type=media_type, headers=headers
            )
        plugin = get_plugin_for_value(data, request.app.plugins)
        if plugin:
            if isinstance(data, (list, tuple)):
                data = [plugin.to_dict(datum) for datum in data]
            else:
                data = plugin.to_dict(data)
        response_class = self.resolve_response_class()
        return response_class(
            headers=headers,
            status_code=status_code,
            content=data,
            media_type=media_type,
        )


route = HTTPRouteHandler


class get(HTTPRouteHandler):
    http_method: Literal[HttpMethod.GET] = Field(default=HttpMethod.GET, const=True)


class post(HTTPRouteHandler):
    http_method: Literal[HttpMethod.POST] = Field(default=HttpMethod.POST, const=True)


class put(HTTPRouteHandler):
    http_method: Literal[HttpMethod.PUT] = Field(default=HttpMethod.PUT, const=True)


class patch(HTTPRouteHandler):
    http_method: Literal[HttpMethod.PATCH] = Field(default=HttpMethod.PATCH, const=True)


class delete(HTTPRouteHandler):
    http_method: Literal[HttpMethod.DELETE] = Field(default=HttpMethod.DELETE, const=True)


class WebsocketRouteHandler(BaseRouteHandler):
    def __call__(self, fn: AnyCallable) -> "WebsocketRouteHandler":
        """
        Replaces a function with itself
        """
        self.fn = fn
        self.validate_handler_function()
        return self

    def validate_handler_function(self) -> None:
        """
        Validates the route handler function once it's set by inspecting its return annotations
        """
        super().validate_handler_function()
        signature = Signature.from_callable(cast(AnyCallable, self.fn))

        if signature.return_annotation is not None:
            raise ImproperlyConfiguredException("websocket handler functions should return 'None'")
        if "socket" not in signature.parameters:
            raise ImproperlyConfiguredException("websocket handlers must set a 'socket' kwarg")

    async def handle_websocket(self, web_socket: WebSocket) -> None:
        """
        Handles a given Websocket in relation to self.
        """
        if not self.fn:
            raise ImproperlyConfiguredException("cannot call a route handler without a decorated function")
        await self.authorize_connection(connection=web_socket)
        params = await self.get_parameters_from_connection(connection=web_socket)
        if isinstance(self.owner, Controller):
            await self.fn(self.owner, **params)
        else:
            await self.fn(**params)


websocket = WebsocketRouteHandler
