from dataclasses import dataclass, field
from inspect import cleandoc
from typing import TYPE_CHECKING, Any, cast

from litestar._openapi.utils import SEPARATORS_CLEANUP_PATTERN
from litestar.enums import HttpMethod, ParamType
from litestar.exceptions import HTTPException, ValidationException
from litestar.openapi.spec import Operation
from litestar.params import ParameterKwarg, PathParameter
from litestar.status_codes import HTTP_204_NO_CONTENT, HTTP_304_NOT_MODIFIED
from litestar.typing import FieldDefinition
from litestar.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from litestar.datastructures import Cookie, ResponseHeader
    from litestar.dto import AbstractDTO
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.datastructures import ResponseSpec
    from litestar.openapi.spec import SecurityRequirement
    from litestar.types.internal_types import PathParameterDefinition

__all__ = (
    "OperationDescription",
    "RequestBodyDescription",
    "ResponseDescription",
    "describe_operation",
)


@dataclass(frozen=True)
class RequestBodyDescription:
    """The request body an operation reads."""

    field_definition: FieldDefinition
    dto: "type[AbstractDTO] | None" = None


@dataclass(frozen=True)
class ResponseDescription:
    """The response an operation sends on success."""

    status_code: int
    return_type: FieldDefinition
    media_type: str = ""
    description: str | None = None
    dto: "type[AbstractDTO] | None" = None
    headers: "tuple[ResponseHeader, ...]" = ()
    cookies: "tuple[Cookie, ...]" = ()
    content_encoding: str | None = None
    content_media_type: str | None = None
    allows_body: bool = True


@dataclass(frozen=True)
class OperationDescription:
    """Everything the OpenAPI generation needs to know about one operation.

    This is the only input of the functions creating an :class:`~litestar.openapi.spec.Operation`; they never read
    the route handler itself.
    """

    handler_id: str
    operation_id: str
    summary: str
    response: ResponseDescription
    description: str | None = None
    tags: tuple[str, ...] = ()
    deprecated: bool = False
    security: "tuple[SecurityRequirement, ...] | None" = None
    """Security requirements. ``None`` inherits the document's requirements, an empty tuple lifts them."""
    parameters: tuple[tuple[str, FieldDefinition], ...] = ()
    """Name and field definition of every parameter, in the order they are documented."""
    request_body: RequestBodyDescription | None = None
    raises: tuple[type[HTTPException], ...] = ()
    additional_responses: "Mapping[int, ResponseSpec]" = field(default_factory=dict)
    allows_response_body: bool = True
    """Whether any response of the operation may have content, which a response to ``HEAD`` may not."""
    operation_class: type[Operation] = Operation
    signature_namespace: dict[str, Any] = field(default_factory=dict)


def describe_operation(
    route_handler: "HTTPRouteHandler",
    http_method: HttpMethod,
    openapi_config: "OpenAPIConfig",
    path_components: "Sequence[str | PathParameterDefinition]" = (),
    path_parameters: "Mapping[str, PathParameterDefinition] | None" = None,
) -> OperationDescription:
    """Describe the operation a route handler serves for an HTTP method.

    Args:
        route_handler: A registered route handler.
        http_method: The HTTP method of the operation.
        openapi_config: The OpenAPI config.
        path_components: The components of the route's path.
        path_parameters: The path parameters of the route.

    Returns:
        An operation description.
    """
    if isinstance(route_handler.operation_id, str):
        operation_id = route_handler.operation_id
    else:
        operation_id_creator = route_handler.operation_id or openapi_config.operation_id_creator
        operation_id = operation_id_creator(route_handler, http_method, list(path_components))

    description = route_handler.description
    if description is None and openapi_config.use_handler_docstrings:
        fn = unwrap_partial(route_handler.fn)
        description = cleandoc(fn.__doc__) if fn.__doc__ else None

    parameters = _collect_parameter_fields(route_handler, path_parameters or {})
    request_body = _describe_request_body(route_handler)

    raises = tuple(route_handler.raises or ())
    if (request_body or parameters) and ValidationException not in raises:
        raises = (*raises, ValidationException)

    status_code = route_handler.status_code

    return OperationDescription(
        handler_id=route_handler.handler_id,
        operation_id=operation_id,
        summary=route_handler.summary or SEPARATORS_CLEANUP_PATTERN.sub("", route_handler.handler_name.title()),
        description=description,
        tags=tuple(sorted(route_handler.tags)),
        deprecated=route_handler.deprecated,
        security=route_handler.security if route_handler.security or route_handler._security_opt_out else None,
        parameters=parameters,
        request_body=request_body,
        response=ResponseDescription(
            status_code=status_code,
            return_type=route_handler.parsed_fn_signature.return_type,
            media_type=route_handler.media_type,
            description=route_handler.response_description,
            dto=route_handler.return_dto,
            headers=tuple(route_handler.response_headers),
            cookies=tuple(route_handler.response_cookies),
            content_encoding=route_handler.content_encoding,
            content_media_type=route_handler.content_media_type,
            allows_body=not (
                http_method == HttpMethod.HEAD
                or status_code < 200
                or status_code in {HTTP_204_NO_CONTENT, HTTP_304_NOT_MODIFIED}
            ),
        ),
        raises=raises,
        additional_responses=route_handler.responses or {},
        allows_response_body=http_method != HttpMethod.HEAD,
        operation_class=route_handler.operation_class,
        signature_namespace=route_handler.signature_namespace,
    )


def _describe_request_body(route_handler: "HTTPRouteHandler") -> RequestBodyDescription | None:
    """Describe the request body the handler or one of its providers declares.

    The handler's DTO decodes the body only if the handler itself declares it.
    """
    setup = route_handler._injection_setup
    body = next((definition for definition in setup.request_parameter_definitions.values() if definition.is_body), None)
    if body is None:
        return None
    handler_declares_body = any(parameter.is_body for parameter in setup.target.request_parameters)
    return RequestBodyDescription(body.field_definition, route_handler.data_dto if handler_declares_body else None)


def _collect_parameter_fields(
    route_handler: "HTTPRouteHandler", path_parameters: "Mapping[str, PathParameterDefinition]"
) -> tuple[tuple[str, FieldDefinition], ...]:
    """Collect the parameters the handler reads from the request, through its function, providers and layers, and
    the path parameters of the route it does not read. Path parameters come first, in the order of the path.
    """
    collected: list[tuple[str, FieldDefinition]] = []
    declared_path_parameters: set[str] = set()
    for definition in route_handler._injection_setup.request_parameter_definitions.values():
        if definition.is_body:
            continue
        if definition.param_type is ParamType.PATH:
            declared_path_parameters.add(definition.name)
            if definition.name not in path_parameters:
                continue
        if cast("ParameterKwarg", definition.field_definition.kwarg_definition).include_in_schema:
            collected.append((definition.name, definition.field_definition))
    collected.extend(
        (name, FieldDefinition.from_kwarg(parameter.type, name=name, kwarg_definition=PathParameter(name=name)))
        for name, parameter in path_parameters.items()
        if name not in declared_path_parameters
    )

    positions = {name: index for index, name in enumerate(path_parameters)}

    def path_position(parameter: tuple[str, FieldDefinition]) -> int:
        name, field_definition = parameter
        if cast("ParameterKwarg", field_definition.kwarg_definition).param_type is ParamType.PATH:
            return positions.get(name, len(positions))
        return len(positions)

    return tuple(sorted(collected, key=path_position))
