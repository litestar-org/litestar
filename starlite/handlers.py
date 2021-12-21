from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Extra, Field, validator
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from typing_extensions import Literal

from starlite.controller import Controller
from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import HTTPException, ImproperlyConfiguredException
from starlite.provide import Provide
from starlite.utils.model import create_function_signature_model

if TYPE_CHECKING:  # pragma: no cover
    from starlite.routing import Router


class RouteHandler(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.allow

    http_method: Union[HttpMethod, List[HttpMethod]]
    status_code: Optional[int] = None
    include_in_schema: bool = True
    media_type: Optional[Union[MediaType, str]] = None
    path: Optional[str] = None
    response_class: Optional[Type[Response]] = None
    response_headers: Optional[BaseModel] = None
    dependencies: Optional[Dict[str, Provide]] = None

    fn: Optional[Callable] = None
    owner: Optional[Union[Controller, "Router"]] = None
    resolved_dependencies: Optional[Dict[str, Provide]]
    signature_model: Optional[Type[BaseModel]] = None

    # OpenAPI attributes
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    operation_id: Optional[str] = None
    deprecated: bool = False
    raises: Optional[List[Type[HTTPException]]] = None

    def __call__(self, fn: Callable) -> "RouteHandler":
        """
        Replaces a function with itself
        """
        self.fn = fn
        self.signature_model = create_function_signature_model(fn)
        return self

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
    def validate_dependency_is_unique(dependencies: Dict[str, Provide], key: str, provider: Provide):
        """
        Validates that a given provider has not been already defined under a different key
        """
        for dependency_key, value in dependencies.items():
            if provider == value:
                raise ImproperlyConfiguredException(
                    f"Provider for key {key} is already defined under the different key {dependency_key}. "
                    f"If you wish to override a provider, it must have the same key."
                )

    def resolve_dependencies(self) -> Dict[str, Provide]:
        """
        Returns all dependencies correlating to handler.fn kwargs in the given handler's scopes
        """
        assert self.signature_model, "resolve_dependencies cannot be called before a signature model has been generated"
        if self.resolved_dependencies is None:
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
        return self.resolved_dependencies


route = RouteHandler


class get(RouteHandler):
    http_method: Literal[HttpMethod.GET] = Field(default=HttpMethod.GET)


class post(RouteHandler):
    http_method: Literal[HttpMethod.POST] = Field(default=HttpMethod.POST)


class put(RouteHandler):
    http_method: Literal[HttpMethod.PUT] = Field(default=HttpMethod.PUT)


class patch(RouteHandler):
    http_method: Literal[HttpMethod.PATCH] = Field(default=HttpMethod.PATCH)


class delete(RouteHandler):
    http_method: Literal[HttpMethod.DELETE] = Field(default=HttpMethod.DELETE)
