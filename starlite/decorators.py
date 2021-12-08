from typing import Any, Callable, List, Optional, Union

from pydantic import BaseModel, validate_arguments, validator
from starlette.responses import Response
from typing_extensions import Type

from starlite.enums import HttpMethod, MediaType


class RouteInfo(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    http_method: Union[HttpMethod, List[HttpMethod]]
    include_in_schema: Optional[bool] = None
    media_type: Optional[MediaType] = None
    name: Optional[str] = None
    path: Optional[str] = None
    response_class: Optional[Type[Response]] = None
    response_headers: Optional[Union[dict, BaseModel]] = None
    status_code: Optional[int] = None

    @classmethod
    @validator("http_method")
    def validate_http_method(cls, value: Any) -> Optional[Union[HttpMethod, List[HttpMethod]]]:
        """Validates that a given value is either None, HttpMethod enum member or list thereof"""
        if (
            value is None
            or HttpMethod.is_http_method(value)
            or (isinstance(value, list) and len(value) > 0 and all(HttpMethod.is_http_method(v) for v in value))
        ):
            return value
        raise ValueError()

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
    http_method: Union[HttpMethod, List[HttpMethod]],
    include_in_schema: Optional[bool] = None,
    media_type: Optional[MediaType] = None,
    name: Optional[str] = None,
    path: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
) -> Callable:
    """Decorator that wraps a given method and sets an instance of RouteInfo as an attribute of the returned method"""

    def decorator(function: Callable):
        route_info = RouteInfo(
            http_method=http_method,
            include_in_schema=include_in_schema,
            media_type=media_type,
            name=name,
            path=path,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
        )
        setattr(function, "route_info", route_info)
        return function

    return decorator


@validate_arguments
def get(
    *,
    include_in_schema: Optional[bool] = None,
    media_type: Optional[MediaType] = None,
    name: Optional[str] = None,
    path: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
):
    """Route decorator with pre-set http_method GET"""
    return route(
        http_method=HttpMethod.GET,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        path=path,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
    )


@validate_arguments
def post(
    *,
    include_in_schema: Optional[bool] = None,
    media_type: Optional[MediaType] = None,
    name: Optional[str] = None,
    path: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
):
    """Route decorator with pre-set http_method POST"""
    return route(
        http_method=HttpMethod.POST,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        path=path,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
    )


@validate_arguments
def put(
    *,
    include_in_schema: Optional[bool] = None,
    media_type: Optional[MediaType] = None,
    name: Optional[str] = None,
    path: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
):
    """Route decorator with pre-set http_method PUT"""
    return route(
        http_method=HttpMethod.PUT,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        path=path,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
    )


@validate_arguments
def patch(
    *,
    include_in_schema: Optional[bool] = None,
    media_type: Optional[MediaType] = None,
    name: Optional[str] = None,
    path: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
):
    """Route decorator with pre-set http_method PATCH"""
    return route(
        http_method=HttpMethod.PATCH,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        path=path,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
    )


@validate_arguments
def delete(
    *,
    include_in_schema: Optional[bool] = None,
    media_type: Optional[MediaType] = None,
    name: Optional[str] = None,
    path: Optional[str] = None,
    response_class: Optional[Type[Response]] = None,
    response_headers: Optional[Union[dict, BaseModel]] = None,
    status_code: Optional[int] = None,
):
    """Route decorator with pre-set http_method DELETE"""
    return route(
        http_method=HttpMethod.DELETE,
        include_in_schema=include_in_schema,
        media_type=media_type,
        name=name,
        path=path,
        response_class=response_class,
        response_headers=response_headers,
        status_code=status_code,
    )
