from inspect import Signature, isclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from pydantic import BaseModel, Extra, Field, validator
from pydantic.typing import AnyCallable
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
from starlite.provide import Provide
from starlite.response import Response
from starlite.types import File, Guard, Redirect, ResponseHeader
from starlite.utils.model import create_function_signature_model

if TYPE_CHECKING:  # pragma: no cover
    from starlite.routing import Router


class _empty:
    """Placeholder"""


class RouteHandler(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.allow

    dependencies: Optional[Dict[str, Provide]] = None
    guards: Optional[List[Guard]] = None
    http_method: Union[HttpMethod, List[HttpMethod]]
    include_in_schema: bool = True
    media_type: Union[MediaType, str] = MediaType.JSON
    path: Optional[str] = None
    response_class: Optional[Type[Response]] = None
    response_headers: Optional[Dict[str, ResponseHeader]] = None
    status_code: Optional[int] = None
    opt: Dict[str, Any] = {}

    fn: Optional[AnyCallable] = None
    owner: Optional[Union[Controller, "Router"]] = None
    resolved_dependencies: Union[Dict[str, Provide], Type[_empty]] = _empty
    resolved_headers: Union[Dict[str, ResponseHeader], Type[_empty]] = _empty
    resolved_response_class: Union[Type[Response], Type[_empty]] = _empty
    resolved_guards: Union[List[Guard], Type[_empty]] = _empty
    signature_model: Optional[Type[BaseModel]] = None

    # OpenAPI attributes
    content_encoding: Optional[str] = None
    content_media_type: Optional[str] = None
    deprecated: bool = False
    description: Optional[str] = None
    operation_id: Optional[str] = None
    raises: Optional[List[Type[HTTPException]]] = None
    response_description: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None

    def __call__(self, fn: AnyCallable) -> "RouteHandler":
        """
        Replaces a function with itself
        """
        self.fn = fn
        self.signature_model = create_function_signature_model(fn)
        self.validate_handler_function()
        return self

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

    def resolve_dependencies(self) -> Dict[str, Provide]:
        """
        Returns all dependencies correlating to handler function's kwargs that exist in the handler's scope
        """
        assert self.signature_model, "resolve_dependencies cannot be called before a signature model has been generated"
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
        Validates the route handler function once its set by inspecting its return annotations
        """
        assert self.fn, "cannot call validate_handler_function without first setting self.fn"

        return_annotation = Signature.from_callable(self.fn).return_annotation
        if return_annotation is Signature.empty:
            raise ValidationException(
                "A return value of a route handler function should be type annotated."
                "If your function doesn't return a value or returns None, annotate it as returning None."
            )
        if isclass(return_annotation):
            if issubclass(return_annotation, Redirect) and self.status_code not in REDIRECT_STATUS_CODES:
                raise ValidationException(
                    f"Redirect responses should have one of "
                    f"the following status codes: {', '.join([str(s) for s in REDIRECT_STATUS_CODES])}"
                )
            if issubclass(return_annotation, File) and self.media_type in [MediaType.JSON, MediaType.HTML]:
                self.media_type = MediaType.TEXT


route = RouteHandler


class get(RouteHandler):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.allow

    http_method: Literal[HttpMethod.GET] = Field(default=HttpMethod.GET, const=True)


class post(RouteHandler):
    http_method: Literal[HttpMethod.POST] = Field(default=HttpMethod.POST, const=True)


class put(RouteHandler):
    http_method: Literal[HttpMethod.PUT] = Field(default=HttpMethod.PUT, const=True)


class patch(RouteHandler):
    http_method: Literal[HttpMethod.PATCH] = Field(default=HttpMethod.PATCH, const=True)


class delete(RouteHandler):
    http_method: Literal[HttpMethod.DELETE] = Field(default=HttpMethod.DELETE, const=True)
