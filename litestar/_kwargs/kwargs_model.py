from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from anyio import create_task_group

from litestar._kwargs.cleanup import DependencyCleanupGroup
from litestar._kwargs.dependencies import (
    Dependency,
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
from litestar._signature import SignatureModel, get_signature_model
from litestar._signature.field import SignatureField
from litestar.constants import RESERVED_KWARGS
from litestar.dto.interface import DTOInterface
from litestar.enums import ParamType, RequestEncodingType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import BodyKwarg, ParameterKwarg

__all__ = ("KwargsModel",)


if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.di import Provide
    from litestar.utils.signature import ParsedParameter, ParsedSignature


class KwargsModel:
    """Model required kwargs for a given RouteHandler and its dependencies.

    This is done once and is memoized during application bootstrap, ensuring minimal runtime overhead.
    """

    __slots__ = (
        "dependency_batches",
        "expected_cookie_params",
        "expected_dto_data",
        "expected_form_data",
        "expected_msgpack_data",
        "expected_header_params",
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
        expected_dto_data: tuple[ParsedParameter, type[DTOInterface]] | None,
        expected_dependencies: set[Dependency],
        expected_form_data: tuple[RequestEncodingType | str, SignatureField] | None,
        expected_msgpack_data: SignatureField | None,
        expected_header_params: set[ParameterDefinition],
        expected_path_params: set[ParameterDefinition],
        expected_query_params: set[ParameterDefinition],
        expected_reserved_kwargs: set[str],
        sequence_query_parameter_names: set[str],
        is_data_optional: bool,
    ) -> None:
        """Initialize ``KwargsModel``.

        Args:
            expected_cookie_params: Any expected cookie parameter kwargs
            expected_dependencies: Any expected dependency kwargs
            expected_dto_data: Any expected DTO data kwargs
            expected_form_data: Any expected form data kwargs
            expected_msgpack_data: Any expected MessagePack data kwargs
            expected_header_params: Any expected header parameter kwargs
            expected_path_params: Any expected path parameter kwargs
            expected_query_params: Any expected query parameter kwargs
            expected_reserved_kwargs: Any expected reserved kwargs, e.g. 'state'
            sequence_query_parameter_names: Any query parameters that are sequences
            is_data_optional: Treat data as optional
        """
        self.expected_cookie_params = expected_cookie_params
        self.expected_dto_data = expected_dto_data
        self.expected_form_data = expected_form_data
        self.expected_msgpack_data = expected_msgpack_data
        self.expected_header_params = expected_header_params
        self.expected_path_params = expected_path_params
        self.expected_query_params = expected_query_params
        self.expected_reserved_kwargs = expected_reserved_kwargs
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
            or expected_dto_data
        )

        self.is_data_optional = is_data_optional
        self.extractors = self._create_extractors()
        self.dependency_batches = create_dependency_batches(expected_dependencies)

    def _create_extractors(self) -> list[Callable[[dict[str, Any], ASGIConnection], None]]:
        reserved_kwargs_extractors: dict[str, Callable[[dict[str, Any], ASGIConnection], None]] = {
            "data": create_data_extractor(self),
            "state": state_extractor,
            "scope": scope_extractor,
            "request": request_extractor,
            "socket": socket_extractor,
            "headers": headers_extractor,
            "cookies": cookies_extractor,
            "query": query_extractor,
            "body": body_extractor,  # type: ignore
        }

        extractors: list[Callable[[dict[str, Any], ASGIConnection], None]] = [
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
        layered_parameters: dict[str, SignatureField],
        dependencies: dict[str, Provide],
        signature_fields: dict[str, SignatureField],
    ) -> tuple[set[ParameterDefinition], set[Dependency]]:
        """Get parameter_definitions for the construction of KwargsModel instance.

        Args:
            path_parameters: Any expected path parameters.
            layered_parameters: A string keyed dictionary of layered parameters.
            dependencies: A string keyed dictionary mapping dependency providers.
            signature_fields: The SignatureModel fields.

        Returns:
            A Tuple of sets
        """
        expected_dependencies = {
            cls._create_dependency_graph(key=key, dependencies=dependencies)
            for key in dependencies
            if key in signature_fields
        }
        ignored_keys = {*RESERVED_KWARGS, *(dependency.key for dependency in expected_dependencies)}

        param_definitions = {
            *(
                create_parameter_definition(
                    signature_field=signature_field,
                    field_name=field_name,
                    path_parameters=path_parameters,
                )
                for field_name, signature_field in layered_parameters.items()
                if field_name not in ignored_keys and field_name not in signature_fields
            ),
            *(
                create_parameter_definition(
                    signature_field=signature_field,
                    field_name=field_name,
                    path_parameters=path_parameters,
                )
                for field_name, signature_field in signature_fields.items()
                if field_name not in ignored_keys and field_name not in layered_parameters
            ),
        }

        for field_name, signature_field in (
            (k, v) for k, v in signature_fields.items() if k not in ignored_keys and k in layered_parameters
        ):
            layered_parameter = layered_parameters[field_name]
            field = signature_field if signature_field.is_parameter_field else layered_parameter
            default_value = (
                signature_field.default_value if not signature_field.is_empty else layered_parameter.default_value
            )

            param_definitions.add(
                create_parameter_definition(
                    signature_field=SignatureField(
                        name=field.name,
                        default_value=default_value,
                        children=field.children,
                        field_type=field.field_type,
                        kwarg_model=field.kwarg_model,
                        extra=field.extra,
                    ),
                    field_name=field_name,
                    path_parameters=path_parameters,
                )
            )

        return param_definitions, expected_dependencies

    @classmethod
    def create_for_signature_model(
        cls,
        signature_model: type[SignatureModel],
        parsed_signature: ParsedSignature,
        dependencies: dict[str, Provide],
        path_parameters: set[str],
        layered_parameters: dict[str, SignatureField],
        data_dto: type[DTOInterface] | None,
    ) -> KwargsModel:
        """Pre-determine what parameters are required for a given combination of route + route handler. It is executed
        during the application bootstrap process.

        Args:
            signature_model: A :class:`SignatureModel <litestar._signature.SignatureModel>` subclass.
            parsed_signature: A :class:`ParsedSignature <litestar._signature.ParsedSignature>` instance.
            dependencies: A string keyed dictionary mapping dependency providers.
            path_parameters: Any expected path parameters.
            layered_parameters: A string keyed dictionary of layered parameters.
            data_dto: A :class:`DTOInterface <litestar._dto.DTOInterface>` subclass if one is declared
                for the route handler, or ``None``.

        Returns:
            An instance of KwargsModel
        """

        signature_fields = signature_model.fields

        cls._validate_raw_kwargs(
            path_parameters=path_parameters,
            dependencies=dependencies,
            signature_fields=signature_fields,
            layered_parameters=layered_parameters,
        )

        param_definitions, expected_dependencies = cls._get_param_definitions(
            path_parameters=path_parameters,
            layered_parameters=layered_parameters,
            dependencies=dependencies,
            signature_fields=signature_fields,
        )

        expected_reserved_kwargs = {field_name for field_name in signature_fields if field_name in RESERVED_KWARGS}
        expected_path_parameters = {p for p in param_definitions if p.param_type == ParamType.PATH}
        expected_header_parameters = {p for p in param_definitions if p.param_type == ParamType.HEADER}
        expected_cookie_parameters = {p for p in param_definitions if p.param_type == ParamType.COOKIE}
        expected_query_parameters = {p for p in param_definitions if p.param_type == ParamType.QUERY}
        sequence_query_parameter_names = {p.field_alias for p in expected_query_parameters if p.is_sequence}

        expected_form_data: tuple[RequestEncodingType | str, SignatureField] | None = None
        expected_msgpack_data: SignatureField | None = None
        expected_dto_data: tuple[ParsedParameter, type[DTOInterface]] | None = None

        data_signature_field = signature_fields.get("data")

        media_type: RequestEncodingType | str | None = None
        if data_signature_field and isinstance(data_signature_field.kwarg_model, BodyKwarg):
            media_type = data_signature_field.kwarg_model.media_type

        if data_signature_field and media_type:
            if media_type in (
                RequestEncodingType.MULTI_PART,
                RequestEncodingType.URL_ENCODED,
            ):
                expected_form_data = (media_type, data_signature_field)

            elif media_type == RequestEncodingType.MESSAGEPACK:
                expected_msgpack_data = data_signature_field

        elif data_signature_field:
            parsed_parameter = parsed_signature.parameters["data"]
            parsed_type = parsed_parameter.parsed_type
            if parsed_type.is_subclass_of(DTOInterface):
                expected_dto_data = (parsed_parameter, parsed_type.annotation)
            elif data_dto:
                expected_dto_data = (parsed_parameter, data_dto)

        for dependency in expected_dependencies:
            dependency_kwargs_model = cls.create_for_signature_model(
                signature_model=get_signature_model(dependency.provide),
                parsed_signature=parsed_signature,
                dependencies=dependencies,
                path_parameters=path_parameters,
                layered_parameters=layered_parameters,
                data_dto=None,
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

            if "data" in expected_reserved_kwargs and "data" in dependency_kwargs_model.expected_reserved_kwargs:
                cls._validate_dependency_data(
                    expected_form_data=expected_form_data,
                    dependency_kwargs_model=dependency_kwargs_model,
                )

            expected_reserved_kwargs.update(dependency_kwargs_model.expected_reserved_kwargs)
            sequence_query_parameter_names.update(dependency_kwargs_model.sequence_query_parameter_names)

        return KwargsModel(
            expected_cookie_params=expected_cookie_parameters,
            expected_dependencies=expected_dependencies,
            expected_dto_data=expected_dto_data,
            expected_form_data=expected_form_data,
            expected_header_params=expected_header_parameters,
            expected_msgpack_data=expected_msgpack_data,
            expected_path_params=expected_path_parameters,
            expected_query_params=expected_query_parameters,
            expected_reserved_kwargs=expected_reserved_kwargs,
            is_data_optional=signature_fields["data"].is_optional if "data" in expected_reserved_kwargs else False,
            sequence_query_parameter_names=sequence_query_parameter_names,
        )

    def to_kwargs(self, connection: ASGIConnection) -> dict[str, Any]:
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
            extractor(output, connection)

        return output

    async def resolve_dependencies(
        self, connection: "ASGIConnection", kwargs: dict[str, Any]
    ) -> "DependencyCleanupGroup":
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
                async with create_task_group() as task_group:
                    for dependency in batch:
                        task_group.start_soon(resolve_dependency, dependency, connection, kwargs, cleanup_group)
        return cleanup_group

    @classmethod
    def _create_dependency_graph(cls, key: str, dependencies: dict[str, Provide]) -> Dependency:
        """Create a graph like structure of dependencies, with each dependency including its own dependencies as a
        list.
        """
        provide = dependencies[key]
        sub_dependency_keys = [k for k in get_signature_model(provide).fields if k in dependencies]
        return Dependency(
            key=key,
            provide=provide,
            dependencies=[cls._create_dependency_graph(key=k, dependencies=dependencies) for k in sub_dependency_keys],
        )

    @classmethod
    def _validate_dependency_data(
        cls,
        expected_form_data: tuple[RequestEncodingType | str, SignatureField] | None,
        dependency_kwargs_model: KwargsModel,
    ) -> None:
        """Validate that the 'data' kwarg is compatible across dependencies."""
        if bool(expected_form_data) != bool(dependency_kwargs_model.expected_form_data):
            raise ImproperlyConfiguredException(
                "Dependencies have incompatible 'data' kwarg types: one expects JSON and the other expects form-data"
            )
        if expected_form_data and dependency_kwargs_model.expected_form_data:
            local_media_type, _ = expected_form_data
            dependency_media_type, _ = dependency_kwargs_model.expected_form_data
            if local_media_type != dependency_media_type:
                raise ImproperlyConfiguredException(
                    "Dependencies have incompatible form-data encoding: one expects url-encoded and the other expects multi-part"
                )

    @classmethod
    def _validate_raw_kwargs(
        cls,
        path_parameters: set[str],
        dependencies: dict[str, Provide],
        signature_fields: dict[str, SignatureField],
        layered_parameters: dict[str, SignatureField],
    ) -> None:
        """Validate that there are no ambiguous kwargs, that is, kwargs declared using the same key in different
        places.
        """
        dependency_keys = set(dependencies.keys())

        parameter_names = {
            *(
                k
                for k, f in signature_fields.items()
                if isinstance(f.kwarg_model, ParameterKwarg)
                and (f.kwarg_model.header or f.kwarg_model.query or f.kwarg_model.cookie)
            ),
            *list(layered_parameters.keys()),
        }

        for intersection in (
            path_parameters.intersection(dependency_keys)
            or path_parameters.intersection(parameter_names)
            or dependency_keys.intersection(parameter_names)
        ):
            if intersection:
                raise ImproperlyConfiguredException(
                    f"Kwarg resolution ambiguity detected for the following keys: {', '.join(intersection)}. "
                    f"Make sure to use distinct keys for your dependencies, path parameters and aliased parameters."
                )

        used_reserved_kwargs = {*parameter_names, *path_parameters, *dependency_keys}.intersection(RESERVED_KWARGS)
        if used_reserved_kwargs:
            raise ImproperlyConfiguredException(
                f"Reserved kwargs ({', '.join(RESERVED_KWARGS)}) cannot be used for dependencies and parameter arguments. "
                f"The following kwargs have been used: {', '.join(used_reserved_kwargs)}"
            )
