from __future__ import annotations

import dataclasses
import warnings
from typing import TYPE_CHECKING, Any

from anyio import create_task_group

from litestar._kwargs.cleanup import DependencyCleanupGroup
from litestar._kwargs.dependencies import (
    DependencyContainer,
    create_dependency_batches,
    resolve_dependency,
)
from litestar._kwargs.extractors import (
    body_extractor,
    cookies_extractor,
    create_connection_value_extractor,
    create_data_extractor,
    headers_extractor,
    parse_connection_headers,
    parse_connection_query_params,
    query_extractor,
    request_extractor,
    scope_extractor,
    socket_extractor,
    state_extractor,
)
from litestar._kwargs.parameter_definition import (
    ParameterDefinition,
    create_parameter_definition,
    merge_parameter_sets,
)
from litestar.constants import RESERVED_KWARGS
from litestar.enums import ParamType, RequestEncodingType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.exceptions.base_exceptions import LitestarDeprecationWarning
from litestar.params import BodyKwarg, ParameterKwarg
from litestar.typing import FieldDefinition
from litestar.utils.helpers import get_exception_group

__all__ = ("KwargsModel",)


if TYPE_CHECKING:
    from litestar._kwargs.types import Extractor
    from litestar._signature import SignatureModel
    from litestar.connection import ASGIConnection
    from litestar.di import Provide
    from litestar.dto import AbstractDTO
    from litestar.handlers import BaseRouteHandler
    from litestar.utils.signature import ParsedSignature


_ExceptionGroup = get_exception_group()


@dataclasses.dataclass
class HandlerContext:
    handler: str
    paths: list[str]
    dependencies: list[str] = dataclasses.field(default_factory=list)

    def format(self, msg: str) -> str:
        paths = ",".join(sorted(self.paths))
        out = f"[paths={paths!r}, handler={self.handler!r}"
        if self.dependencies:
            out += f", dependencies={' -> '.join(self.dependencies[::-1])!r}"
        return out + f"] {msg}"


class KwargsModel:
    """Model required kwargs for a given RouteHandler and its dependencies.

    This is done once and is memoized during application bootstrap, ensuring minimal runtime overhead.
    """

    __slots__ = (
        "dependency_batches",
        "expected_cookie_params",
        "expected_data_dto",
        "expected_form_data",
        "expected_header_params",
        "expected_msgpack_data",
        "expected_path_params",
        "expected_query_params",
        "expected_reserved_kwargs",
        "extractors",
        "has_kwargs",
        "is_data_optional",
        "sequence_query_parameter_names",
    )

    def __init__(
        self,
        *,
        expected_cookie_params: set[ParameterDefinition],
        expected_data_dto: type[AbstractDTO] | None,
        expected_dependencies: set[DependencyContainer],
        expected_form_data: tuple[RequestEncodingType | str, FieldDefinition] | None,
        expected_header_params: set[ParameterDefinition],
        expected_msgpack_data: FieldDefinition | None,
        expected_path_params: set[ParameterDefinition],
        expected_query_params: set[ParameterDefinition],
        expected_reserved_kwargs: set[str],
        is_data_optional: bool,
        sequence_query_parameter_names: set[str],
    ) -> None:
        """Initialize ``KwargsModel``.

        Args:
            expected_cookie_params: Any expected cookie parameter kwargs
            expected_dependencies: Any expected dependency kwargs
            expected_form_data: Any expected form data kwargs
            expected_header_params: Any expected header parameter kwargs
            expected_msgpack_data: Any expected MessagePack data kwargs
            expected_path_params: Any expected path parameter kwargs
            expected_query_params: Any expected query parameter kwargs
            expected_reserved_kwargs: Any expected reserved kwargs, e.g. 'state'
            expected_data_dto: A data DTO, if defined
            is_data_optional: Treat data as optional
            sequence_query_parameter_names: Any query parameters that are sequences
        """
        self.expected_cookie_params = expected_cookie_params
        self.expected_form_data = expected_form_data
        self.expected_header_params = expected_header_params
        self.expected_msgpack_data = expected_msgpack_data
        self.expected_path_params = expected_path_params
        self.expected_query_params = expected_query_params
        self.expected_reserved_kwargs = expected_reserved_kwargs
        self.expected_data_dto = expected_data_dto
        self.sequence_query_parameter_names = tuple(sequence_query_parameter_names)

        self.has_kwargs = (
            expected_cookie_params
            or expected_dependencies
            or expected_form_data
            or expected_msgpack_data
            or expected_header_params
            or expected_path_params
            or expected_query_params
            or expected_reserved_kwargs
            or expected_data_dto
        )

        self.is_data_optional = is_data_optional
        self.extractors: list[Extractor] = self._create_extractors()
        self.dependency_batches = create_dependency_batches(expected_dependencies)

    def _create_extractors(self) -> list[Extractor]:
        reserved_kwargs_extractors: dict[str, Extractor] = {
            "data": create_data_extractor(self),
            "state": state_extractor,
            "scope": scope_extractor,
            "request": request_extractor,
            "socket": socket_extractor,
            "headers": headers_extractor,
            "cookies": cookies_extractor,
            "query": query_extractor,
            "body": body_extractor,  # type: ignore[dict-item]
        }

        extractors: list[Extractor] = [
            reserved_kwargs_extractors[reserved_kwarg] for reserved_kwarg in self.expected_reserved_kwargs
        ]

        if self.expected_header_params:
            extractors.append(
                create_connection_value_extractor(
                    connection_key="headers",
                    expected_params=self.expected_header_params,
                    kwargs_model=self,
                    parser=parse_connection_headers,
                ),
            )

        if self.expected_path_params:
            extractors.append(
                create_connection_value_extractor(
                    connection_key="path_params",
                    expected_params=self.expected_path_params,
                    kwargs_model=self,
                ),
            )

        if self.expected_cookie_params:
            extractors.append(
                create_connection_value_extractor(
                    connection_key="cookies",
                    expected_params=self.expected_cookie_params,
                    kwargs_model=self,
                ),
            )

        if self.expected_query_params:
            extractors.append(
                create_connection_value_extractor(
                    connection_key="query_params",
                    expected_params=self.expected_query_params,
                    kwargs_model=self,
                    parser=parse_connection_query_params,
                ),
            )
        return extractors

    @classmethod
    def _get_param_definitions(
        cls,
        path_parameters: set[str],
        layered_parameters: dict[str, FieldDefinition],
        dependencies: dict[str, Provide],
        field_definitions: dict[str, FieldDefinition],
    ) -> tuple[set[ParameterDefinition], set[DependencyContainer]]:
        """Get parameter_definitions for the construction of KwargsModel instance.

        Args:
            path_parameters: Any expected path parameters.
            layered_parameters: A string keyed dictionary of layered parameters.
            dependencies: A string keyed dictionary mapping dependency providers.
            field_definitions: The SignatureModel fields.

        Returns:
            A Tuple of sets
        """
        expected_dependencies = {
            cls._create_dependency_graph(key=key, dependencies=dependencies)
            for key in dependencies
            if key in field_definitions
        }
        ignored_keys = {*RESERVED_KWARGS, *(dependency.key for dependency in expected_dependencies)}

        param_definitions = {
            *(
                create_parameter_definition(
                    field_definition=field_definition,
                    field_name=field_name,
                    path_parameters=path_parameters,
                )
                for field_name, field_definition in layered_parameters.items()
                if field_name not in ignored_keys and field_name not in field_definitions
            ),
            *(
                create_parameter_definition(
                    field_definition=field_definition,
                    field_name=field_name,
                    path_parameters=path_parameters,
                )
                for field_name, field_definition in field_definitions.items()
                if field_name not in ignored_keys and field_name not in layered_parameters
            ),
        }

        for field_name, field_definition in (
            (k, v) for k, v in field_definitions.items() if k not in ignored_keys and k in layered_parameters
        ):
            layered_parameter = layered_parameters[field_name]
            field = field_definition if field_definition.is_non_marker_parameter_field else layered_parameter
            default = field_definition.default if field_definition.has_default else layered_parameter.default

            param_definitions.add(
                create_parameter_definition(
                    field_definition=FieldDefinition.from_kwarg(
                        name=field.name,
                        default=default,
                        inner_types=field.inner_types,
                        annotation=field.annotation,
                        kwarg_definition=field.kwarg_definition,
                        extra=field.extra,
                    ),
                    field_name=field_name,
                    path_parameters=path_parameters,
                )
            )

        return param_definitions, expected_dependencies

    @classmethod
    def create_for_signature_model(  # noqa: C901
        cls,
        signature_model: type[SignatureModel],
        parsed_signature: ParsedSignature,
        dependencies: dict[str, Provide],
        path_parameters: set[str],
        layered_parameters: dict[str, FieldDefinition],
        ctx: BaseRouteHandler | HandlerContext | None = None,
    ) -> KwargsModel:
        """Pre-determine what parameters are required for a given combination of route + route handler. It is executed
        during the application bootstrap process.

        Args:
            signature_model: A :class:`SignatureModel <litestar._signature.SignatureModel>` subclass.
            parsed_signature: A :class:`ParsedSignature <litestar._signature.ParsedSignature>` instance.
            dependencies: A string keyed dictionary mapping dependency providers.
            path_parameters: Any expected path parameters.
            layered_parameters: A string keyed dictionary of layered parameters.
            ctx: Route handler / Route handler context

        Returns:
            An instance of KwargsModel
        """

        if ctx is not None and not isinstance(ctx, HandlerContext):
            ctx = HandlerContext(handler=ctx.name or ctx.handler_name, paths=sorted(ctx.paths))

        field_definitions = signature_model._fields

        cls._validate_raw_kwargs(
            path_parameters=path_parameters,
            dependencies=dependencies,
            field_definitions=field_definitions,
            layered_parameters=layered_parameters,
        )

        param_definitions, expected_dependencies = cls._get_param_definitions(
            path_parameters=path_parameters,
            layered_parameters=layered_parameters,
            dependencies=dependencies,
            field_definitions=field_definitions,
        )

        for dep_field_name in dependencies:
            dep_field_def = field_definitions.get(dep_field_name)
            if dep_field_def is None:
                continue
            if not dep_field_def.is_annotated:
                msg = (
                    f"Inferred dependency field {dep_field_name!r}. Mark the field explicitly "
                    f"with 'NamedDependency[{dep_field_def.raw}]'. Inferred dependencies will "
                    "stop working in Litestar 3.0"
                )
                if ctx is not None:
                    msg = ctx.format(msg)
                warnings.warn(
                    msg,
                    category=LitestarDeprecationWarning,
                    stacklevel=2,
                )

        expected_reserved_kwargs = {field_name for field_name in field_definitions if field_name in RESERVED_KWARGS}
        expected_path_parameters = {p for p in param_definitions if p.param_type == ParamType.PATH}
        expected_header_parameters = {p for p in param_definitions if p.param_type == ParamType.HEADER}
        expected_cookie_parameters = {p for p in param_definitions if p.param_type == ParamType.COOKIE}
        expected_query_parameters = {p for p in param_definitions if p.param_type == ParamType.QUERY}
        sequence_query_parameter_names = {p.field_alias for p in expected_query_parameters if p.is_sequence}

        for param in param_definitions:
            # legacy quirk: when using implicit style, dependencies with no providers
            # but a default value are actually treated as query parameters by the
            # injection mechanism, so we add them back as such
            if param.param_type == ParamType.DEPENDENCY:
                expected_query_parameters.add(param)

            if legacy_style := param.legacy_style:
                _warn_deprecated_param_style(
                    style=legacy_style,
                    param_type=param.param_type,
                    field_name=param.field_name,
                    stacklevel=3,
                    ctx=ctx,
                )

        expected_form_data: tuple[RequestEncodingType | str, FieldDefinition] | None = None
        expected_msgpack_data: FieldDefinition | None = None
        expected_data_dto: type[AbstractDTO] | None = None
        data_field_definition = field_definitions.get("data")

        media_type: RequestEncodingType | str | None = None
        if data_field_definition:
            if isinstance(data_field_definition.kwarg_definition, BodyKwarg):
                media_type = data_field_definition.kwarg_definition.media_type

            if media_type in (RequestEncodingType.MULTI_PART, RequestEncodingType.URL_ENCODED):
                expected_form_data = (media_type, data_field_definition)
                expected_data_dto = signature_model._data_dto
            elif signature_model._data_dto:
                expected_data_dto = signature_model._data_dto
            elif media_type == RequestEncodingType.MESSAGEPACK:
                expected_msgpack_data = data_field_definition

        expected_data_field_defs = []

        for dependency in expected_dependencies:
            dependency_kwargs_model = cls.create_for_signature_model(
                signature_model=dependency.provide.signature_model,
                parsed_signature=parsed_signature,
                dependencies=dependencies,
                path_parameters=path_parameters,
                layered_parameters=layered_parameters,
                ctx=dataclasses.replace(ctx, dependencies=[*ctx.dependencies, dependency.key]) if ctx else None,
            )

            expected_path_parameters = merge_parameter_sets(
                expected_path_parameters, dependency_kwargs_model.expected_path_params
            )
            expected_query_parameters = merge_parameter_sets(
                expected_query_parameters, dependency_kwargs_model.expected_query_params
            )
            expected_cookie_parameters = merge_parameter_sets(
                expected_cookie_parameters, dependency_kwargs_model.expected_cookie_params
            )
            expected_header_parameters = merge_parameter_sets(
                expected_header_parameters, dependency_kwargs_model.expected_header_params
            )

            if "data" in dependency_kwargs_model.expected_reserved_kwargs:
                if "data" in expected_reserved_kwargs:
                    cls._validate_dependency_data(
                        expected_form_data=expected_form_data,
                        dependency_kwargs_model=dependency_kwargs_model,
                    )
                expected_data_field_defs.append(dependency.provide.signature_model._fields["data"])

            expected_reserved_kwargs.update(dependency_kwargs_model.expected_reserved_kwargs)
            sequence_query_parameter_names.update(dependency_kwargs_model.sequence_query_parameter_names)

        if handler_data_field := field_definitions.get("data"):
            expected_data_field_defs.append(handler_data_field)

        if expected_data_field_defs:
            cls._validate_data_field_definitions(expected_data_field_defs, ctx)

        is_data_optional = (
            field_definitions["data"].is_optional
            if "data" in expected_reserved_kwargs and "data" in field_definitions
            else False
        )

        return KwargsModel(
            expected_cookie_params=expected_cookie_parameters,
            expected_dependencies=expected_dependencies,
            expected_data_dto=expected_data_dto,
            expected_form_data=expected_form_data,
            expected_header_params=expected_header_parameters,
            expected_msgpack_data=expected_msgpack_data,
            expected_path_params=expected_path_parameters,
            expected_query_params=expected_query_parameters,
            expected_reserved_kwargs=expected_reserved_kwargs,
            is_data_optional=is_data_optional,
            sequence_query_parameter_names=sequence_query_parameter_names,
        )

    async def to_kwargs(self, connection: ASGIConnection) -> dict[str, Any]:
        """Return a dictionary of kwargs. Async values, i.e. CoRoutines, are not resolved to ensure this function is
        sync.

        Args:
            connection: An instance of :class:`Request <litestar.connection.Request>` or
                :class:`WebSocket <litestar.connection.WebSocket>`.

        Returns:
            A string keyed dictionary of kwargs expected by the handler function and its dependencies.
        """
        output: dict[str, Any] = {}

        for extractor in self.extractors:
            await extractor(output, connection)

        return output

    async def resolve_dependencies(self, connection: ASGIConnection, kwargs: dict[str, Any]) -> DependencyCleanupGroup:
        """Resolve all dependencies into the kwargs, recursively.

        Args:
            connection: An instance of :class:`Request <litestar.connection.Request>` or
                :class:`WebSocket <litestar.connection.WebSocket>`.
            kwargs: Kwargs to pass to dependencies.
        """
        cleanup_group = DependencyCleanupGroup()
        for batch in self.dependency_batches:
            if len(batch) == 1:
                await resolve_dependency(next(iter(batch)), connection, kwargs, cleanup_group)
            else:
                try:
                    async with create_task_group() as task_group:
                        for dependency in batch:
                            task_group.start_soon(resolve_dependency, dependency, connection, kwargs, cleanup_group)
                except _ExceptionGroup as excgroup:
                    raise excgroup.exceptions[0] from excgroup  # type: ignore[attr-defined]

        return cleanup_group

    @classmethod
    def _create_dependency_graph(cls, key: str, dependencies: dict[str, Provide]) -> DependencyContainer:
        """Create a graph like structure of dependencies, with each dependency including its own dependencies as a
        list.
        """
        provide = dependencies[key]
        sub_dependency_keys = [k for k in provide.signature_model._fields if k in dependencies]
        return DependencyContainer(
            key=key,
            provide=provide,
            dependencies=[cls._create_dependency_graph(key=k, dependencies=dependencies) for k in sub_dependency_keys],
        )

    @classmethod
    def _validate_dependency_data(
        cls,
        expected_form_data: tuple[RequestEncodingType | str, FieldDefinition] | None,
        dependency_kwargs_model: KwargsModel,
    ) -> None:
        """Validate that the 'data' kwarg is compatible across dependencies."""
        if bool(expected_form_data) != bool(dependency_kwargs_model.expected_form_data):
            raise ImproperlyConfiguredException(
                "Dependencies have incompatible 'data' kwarg types: one expects JSON and the other expects form-data"
            )
        if expected_form_data and dependency_kwargs_model.expected_form_data:
            local_media_type = expected_form_data[0]
            dependency_media_type = dependency_kwargs_model.expected_form_data[0]
            if local_media_type != dependency_media_type:
                raise ImproperlyConfiguredException(
                    "Dependencies have incompatible form-data encoding: one expects url-encoded and the other expects multi-part"
                )

    @classmethod
    def _validate_data_field_definitions(
        cls,
        field_definitions: list[FieldDefinition],
        ctx: HandlerContext | None,
    ) -> None:
        expected_raw_types = []
        seen = set()
        for field_def in field_definitions:
            if field_def.is_any:
                continue
            if field_def.type_ not in seen:
                expected_raw_types.append(field_def.annotation)
            seen.add(field_def.type_)

        if len(seen) > 1:
            expected_types_repr = " <> ".join([f"'{t}'" for t in sorted(expected_raw_types, key=str)])
            msg = f"'data' fields have mismatched types: {expected_types_repr}"
            if ctx is not None:
                msg = ctx.format(msg)
            raise ImproperlyConfiguredException(msg)

    @classmethod
    def _validate_raw_kwargs(
        cls,
        path_parameters: set[str],
        dependencies: dict[str, Provide],
        field_definitions: dict[str, FieldDefinition],
        layered_parameters: dict[str, FieldDefinition],
    ) -> None:
        """Validate that there are no ambiguous kwargs, that is, kwargs declared using the same key in different
        places.
        """
        dependency_keys = set(dependencies.keys())

        parameter_names = {
            *(
                k
                for k, f in field_definitions.items()
                if isinstance(f.kwarg_definition, ParameterKwarg)
                and (
                    f.kwarg_definition.param_type in (ParamType.HEADER, ParamType.QUERY, ParamType.COOKIE)
                    and f.kwarg_definition.name is not None
                )
            ),
            *list(layered_parameters.keys()),
        }

        intersection = (
            path_parameters.intersection(dependency_keys)
            or path_parameters.intersection(parameter_names)
            or dependency_keys.intersection(parameter_names)
        )
        if intersection:
            raise ImproperlyConfiguredException(
                f"Kwarg resolution ambiguity detected for the following keys: {', '.join(intersection)}. "
                f"Make sure to use distinct keys for your dependencies, path parameters, and aliased parameters."
            )

        if used_reserved_kwargs := {
            *parameter_names,
            *path_parameters,
            *dependency_keys,
        }.intersection(RESERVED_KWARGS):
            raise ImproperlyConfiguredException(
                f"Reserved kwargs ({', '.join(RESERVED_KWARGS)}) cannot be used for dependencies and parameter arguments. "
                f"The following kwargs have been used: {', '.join(used_reserved_kwargs)}"
            )


def _warn_deprecated_param_style(
    *,
    style: str,
    param_type: ParamType,
    field_name: str,
    stacklevel: int = 2,
    ctx: HandlerContext | None,
) -> None:
    if param_type == ParamType.DEPENDENCY:
        if style == "default":
            msg = (
                f"Dependency parameter {field_name!r} declared using deprecated default "
                "'param: <type> = Dependency(...)' style. Use "
                "'Annotated[<type>, Dependency(...)]' instead"
            )
        else:
            msg = (
                f"Dependency parameter {field_name!r} declared using deprecated "
                "'param: Annotated[<type>, Dependency(...)]' style. Use "
                "'NamedDependency[<type>]' instead"
            )
    else:
        alternatives = {
            ParamType.QUERY: "FromQuery",
            ParamType.HEADER: "FromHeader",
            ParamType.COOKIE: "FromCookie",
            ParamType.PATH: "FromPath",
        }
        short_alternative = alternatives[param_type]
        param_type_name = param_type.name.lower()
        if style == "inferred":
            msg = (
                f"{param_type_name} parameter {field_name!r} declared using deprecated inferred "
                f"style. Use '{short_alternative}[<type>]' or "
                f"'Annotated[<type>, {param_type.title()}Parameter(...)]' instead"
            )
        elif style == "default":
            msg = (
                f"{param_type_name} parameter {field_name!r} declared using deprecated default "
                f"'param: <type> = Parameter(...)' style. Use '{short_alternative}[<type>]' "
                f"or 'Annotated[<type>, {param_type_name.title()}Parameter(...)]' instead"
            )
        elif style == "annotated":
            msg = (
                f"{param_type_name} parameter {field_name!r} declared using deprecated annotated "
                f"'param: Annotated[<type>, Parameter(...)]' style. Use "
                f"'{short_alternative}[<type>]' or "
                f"'Annotated[<type>, {param_type_name.title()}Parameter(...)]' instead"
            )
        else:
            raise ValueError(f"Unknown style {style!r}")

    if ctx is not None:
        msg = ctx.format(msg)

    warnings.warn(msg, category=LitestarDeprecationWarning, stacklevel=stacklevel)
