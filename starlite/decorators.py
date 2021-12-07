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

    def decorator(method: Callable):
        route_info = RouteInfo(
            http_method=http_method,
            media_type=media_type,
            include_in_schema=include_in_schema,
            name=name,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
            url=url,
        )
        setattr(method, "route_info", route_info)
        return method

    return decorator


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


@validate_arguments
def post(
    *,
    media_type: Optional[MediaType] = None,
    include_in_schema: Optional[bool] = None,
    name: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
    url: Optional[str] = None,
):
    """Route decorator with pre-set http_method POST"""
    return route(
        http_method=HttpMethod.POST,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        url=url,
    )


@validate_arguments
def put(
    *,
    media_type: Optional[MediaType] = None,
    include_in_schema: Optional[bool] = None,
    name: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
    url: Optional[str] = None,
):
    """Route decorator with pre-set http_method PUT"""
    return route(
        http_method=HttpMethod.PUT,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        url=url,
    )


@validate_arguments
def patch(
    *,
    media_type: Optional[MediaType] = None,
    include_in_schema: Optional[bool] = None,
    name: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
    url: Optional[str] = None,
):
    """Route decorator with pre-set http_method PATCH"""
    return route(
        http_method=HttpMethod.PATCH,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        url=url,
    )


@validate_arguments
def delete(
    *,
    media_type: Optional[MediaType] = None,
    include_in_schema: Optional[bool] = None,
    name: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
    url: Optional[str] = None,
):
    """Route decorator with pre-set http_method DELETE"""
    return route(
        http_method=HttpMethod.DELETE,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
        url=url,
    )
