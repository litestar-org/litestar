from functools import wraps
from inspect import getfullargspec, signature
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel, validate_arguments, validator
from starlette.responses import Response
from typing_extensions import Type

from starlite.enums import HttpMethod, MediaType


class RouteInfo(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    http_method: HttpMethod
    media_type: Optional[MediaType] = None
    include_in_schema: Optional[bool] = None
    response_class: Optional[Type[Response]] = None
    name: Optional[str] = None
    response_headers: Optional[Union[dict, BaseModel]] = None
    status_code: Optional[int] = None
    url: Optional[str] = None

    @classmethod
    @validator("response_class")
    def validate_response_class(cls, value: Any) -> Optional[Type[Response]]:
        """valides that value is either None or subclass of Starlette Response"""
        if value is None or issubclass(value, Response):
            return value
        raise ValueError("response_class must be a sub-class of starlette.responses.Response")


@validate_arguments
def route(
    *,
    http_method: HttpMethod,
    media_type: Optional[MediaType] = None,
    include_in_schema: Optional[bool] = None,
    name: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
    url: Optional[str] = None,
) -> Callable:
    """Decorator that wraps a given method and sets an instance of RouteInfo as an attribute of the returned method"""

    def outer_wrapper(method: Callable):
        @wraps(method)
        def inner_wrapper(self, *args, **kwargs) -> Any:
            return method(self, *args, **kwargs)

        setattr(
            inner_wrapper,
            "route_info",
            RouteInfo(
                http_method=http_method,
                media_type=media_type,
                include_in_schema=include_in_schema,
                name=name,
                response_class=response_class,
                response_headers=response_headers,
                status_code=status_code,
                url=url,
            ),
        )
        setattr(inner_wrapper, "annotations", getfullargspec(method).annotations)
        setattr(inner_wrapper, "signature", signature(method))
        return inner_wrapper

    return outer_wrapper


@validate_arguments
def get(
    *,
    media_type: Optional[MediaType] = None,
    include_in_schema: Optional[bool] = None,
    name: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
    url: Optional[str] = None,
):
    """Route decorator with pre-set http_method GET"""
    return route(
        http_method=HttpMethod.GET,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        url=url,
    )
