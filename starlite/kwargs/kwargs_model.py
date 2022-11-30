from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    cast,
)

from anyio import create_task_group
from pydantic.fields import (
    SHAPE_DEQUE,
    SHAPE_FROZENSET,
    SHAPE_LIST,
    SHAPE_SEQUENCE,
    SHAPE_SET,
    SHAPE_TUPLE,
    SHAPE_TUPLE_ELLIPSIS,
    ModelField,
    Undefined,
)
from pydantic_factories.utils import is_optional

from starlite.constants import EXTRA_KEY_IS_PARAMETER, RESERVED_KWARGS
from starlite.datastructures.provide import DependencyCleanupGroup, Provide
from starlite.enums import ParamType, RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.kwargs.dependencies import (
    Dependency,
    create_dependency_batches,
    resolve_dependency,
)
from starlite.kwargs.extractors import (
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
from starlite.kwargs.parameter_definition import (
    ParameterDefinition,
    create_parameter_definition,
    merge_parameter_sets,
)
from starlite.signature import SignatureModel, get_signature_model

if TYPE_CHECKING:
    from starlite.connection import ASGIConnection
    from starlite.types import ReservedKwargs


class KwargsModel:
    """Model required kwargs for a given RouteHandler and its dependencies.

    This is done once and is memoized during application bootstrap, ensuring minimal runtime overhead.
    """

    __slots__ = (
        "dependency_batches",
        "expected_cookie_params",
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
        expected_cookie_params: Set[ParameterDefinition],
        expected_dependencies: Set[Dependency],
        expected_form_data: Optional[Tuple[RequestEncodingType, ModelField]],
        expected_msgpack_data: Optional[ModelField],
        expected_header_params: Set[ParameterDefinition],
        expected_path_params: Set[ParameterDefinition],
        expected_query_params: Set[ParameterDefinition],
        expected_reserved_kwargs: Set["ReservedKwargs"],
        sequence_query_parameter_names: Set[str],
        is_data_optional: bool,
    ) -> None:
        """Initialize `KwargsModel`.

        Args:
            expected_cookie_params: Any expected cookie parameter kwargs
            expected_dependencies: Any expected dependency kwargs
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
        )

        self.is_data_optional = is_data_optional
        self.extractors = self._create_extractors()
        self.dependency_batches = create_dependency_batches(expected_dependencies)

    def _create_extractors(self) -> List[Callable[[Dict[str, Any], "ASGIConnection"], None]]:
        reserved_kwargs_extractors: Dict[str, Callable[[Dict[str, Any], "ASGIConnection"], None]] = {
            "data": create_data_extractor(self),
            "state": state_extractor,
            "scope": scope_extractor,
            "request": request_extractor,
            "socket": socket_extractor,
            "headers": headers_extractor,
            "cookies": cookies_extractor,
            "query": query_extractor,
        }

        extractors: List[Callable[[Dict[str, Any], "ASGIConnection"], None]] = [
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
        path_parameters: Set[str],
        layered_parameters: Dict[str, ModelField],
        dependencies: Dict[str, Provide],
        signature_model_fields: Dict[str, ModelField],
    ) -> Tuple[Set[ParameterDefinition], Set[Dependency]]:
        """Get parameter_definitions for the construction of KwargsModel instance.

        Args:
            path_parameters: Any expected path parameters.
            layered_parameters: A string keyed dictionary of layered parameters.
            dependencies: A string keyed dictionary mapping dependency providers.
            signature_model_fields: __fields__ definition from SignatureModel.

        Returns:
            A Tuple of sets
        """
        sequence_shapes = {
            SHAPE_LIST,
            SHAPE_SET,
            SHAPE_SEQUENCE,
            SHAPE_TUPLE,
            SHAPE_TUPLE_ELLIPSIS,
            SHAPE_DEQUE,
            SHAPE_FROZENSET,
        }

        expected_dependencies = {
            cls._create_dependency_graph(key=key, dependencies=dependencies)
            for key in dependencies
            if key in signature_model_fields
        }
        ignored_keys = {*RESERVED_KWARGS, *(dependency.key for dependency in expected_dependencies)}

        param_definitions = {
            *(
                create_parameter_definition(
                    allow_none=model_field.allow_none,
                    field_name=field_name,
                    field_info=model_field.field_info,
                    path_parameters=path_parameters,
                    is_sequence=model_field.shape in sequence_shapes,
                )
                for field_name, model_field in layered_parameters.items()
                if field_name not in ignored_keys and field_name not in signature_model_fields
            ),
            *(
                create_parameter_definition(
                    allow_none=model_field.allow_none,
                    field_name=field_name,
                    field_info=model_field.field_info,
                    path_parameters=path_parameters,
                    is_sequence=model_field.shape in sequence_shapes,
                )
                for field_name, model_field in signature_model_fields.items()
                if field_name not in ignored_keys and field_name not in layered_parameters
            ),
        }

        for field_name, model_field in filter(
            lambda items: items[0] not in ignored_keys and items[0] in layered_parameters,
            signature_model_fields.items(),
        ):
            layer_field_info = layered_parameters[field_name].field_info
            signature_field_info = model_field.field_info

            field_info = layer_field_info
            # allow users to manually override Parameter definition using Parameter
            if signature_field_info.extra.get(EXTRA_KEY_IS_PARAMETER):
                field_info = signature_field_info

            field_info.default = (
                signature_field_info.default
                if signature_field_info.default not in {Undefined, Ellipsis}
                else layer_field_info.default
            )

            param_definitions.add(
                create_parameter_definition(
                    allow_none=model_field.allow_none,
                    field_name=field_name,
                    field_info=field_info,
                    path_parameters=path_parameters,
                    is_sequence=model_field.shape in sequence_shapes,
                )
            )
        return param_definitions, expected_dependencies

    @classmethod
    def create_for_signature_model(
        cls,
        signature_model: Type[SignatureModel],
        dependencies: Dict[str, Provide],
        path_parameters: Set[str],
        layered_parameters: Dict[str, ModelField],
    ) -> "KwargsModel":
        """Pre-determine what parameters are required for a given combination of route + route handler. It is executed
        during the application bootstrap process.

        Args:
            signature_model: A [SignatureModel][starlite.signature.SignatureModel] subclass.
            dependencies: A string keyed dictionary mapping dependency providers.
            path_parameters: Any expected path parameters.
            layered_parameters: A string keyed dictionary of layered parameters.

        Returns:
            An instance of KwargsModel
        """
        cls._validate_raw_kwargs(
            path_parameters=path_parameters,
            dependencies=dependencies,
            model_fields=signature_model.__fields__,
            layered_parameters=layered_parameters,
        )
        expected_reserved_kwargs = {
            field_name for field_name in signature_model.__fields__ if field_name in RESERVED_KWARGS
        }

        param_definitions, expected_dependencies = cls._get_param_definitions(
            path_parameters, layered_parameters, dependencies, signature_model_fields=signature_model.__fields__
        )

        expected_path_parameters = {p for p in param_definitions if p.param_type == ParamType.PATH}
        expected_header_parameters = {p for p in param_definitions if p.param_type == ParamType.HEADER}
        expected_cookie_parameters = {p for p in param_definitions if p.param_type == ParamType.COOKIE}
        expected_query_parameters = {p for p in param_definitions if p.param_type == ParamType.QUERY}
        sequence_query_parameter_names = {p.field_alias for p in expected_query_parameters if p.is_sequence}

        expected_form_data = None
        expected_msgpack_data = None
        data_model_field = signature_model.__fields__.get("data")

        if data_model_field:
            media_type = data_model_field.field_info.extra.get("media_type")
            if media_type in (
                RequestEncodingType.MULTI_PART,
                RequestEncodingType.URL_ENCODED,
            ):
                expected_form_data = (media_type, data_model_field)
            elif media_type == RequestEncodingType.MESSAGEPACK:
                expected_msgpack_data = data_model_field

        for dependency in expected_dependencies:
            dependency_kwargs_model = cls.create_for_signature_model(
                signature_model=get_signature_model(dependency.provide),
                dependencies=dependencies,
                path_parameters=path_parameters,
                layered_parameters=layered_parameters,
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
                    expected_form_data=expected_form_data,  # pyright: ignore
                    dependency_kwargs_model=dependency_kwargs_model,
                )
            expected_reserved_kwargs.update(dependency_kwargs_model.expected_reserved_kwargs)
            sequence_query_parameter_names.update(dependency_kwargs_model.sequence_query_parameter_names)

        return KwargsModel(
            expected_form_data=expected_form_data,  # pyright: ignore
            expected_msgpack_data=expected_msgpack_data,
            expected_dependencies=expected_dependencies,
            expected_path_params=expected_path_parameters,
            expected_query_params=expected_query_parameters,
            expected_cookie_params=expected_cookie_parameters,
            expected_header_params=expected_header_parameters,
            expected_reserved_kwargs=cast("Set[ReservedKwargs]", expected_reserved_kwargs),
            sequence_query_parameter_names=sequence_query_parameter_names,
            is_data_optional=is_optional(signature_model.__fields__["data"])
            if "data" in expected_reserved_kwargs
            else False,
        )

    def to_kwargs(self, connection: "ASGIConnection") -> Dict[str, Any]:
        """Return a dictionary of kwargs. Async values, i.e. CoRoutines, are not resolved to ensure this function is
        sync.

        Args:
            connection: An instance of [Request][starlite.connection.Request] or [WebSocket][starlite.connection.WebSocket].

        Returns:
            A string keyed dictionary of kwargs expected by the handler function and its dependencies.
        """
        output: Dict[str, Any] = {}

        for extractor in self.extractors:
            extractor(output, connection)

        return output

    async def resolve_dependencies(
        self, connection: "ASGIConnection", kwargs: Dict[str, Any]
    ) -> DependencyCleanupGroup:
        """Resolve all dependencies into the kwargs, recursively.

        Args:
            connection: An instance of [Request][starlite.connection.Request] or [WebSocket][starlite.connection.WebSocket].
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
    def _create_dependency_graph(cls, key: str, dependencies: Dict[str, Provide]) -> Dependency:
        """Create a graph like structure of dependencies, with each dependency including its own dependencies as a
        list.
        """
        provide = dependencies[key]
        sub_dependency_keys = [k for k in get_signature_model(provide).__fields__ if k in dependencies]
        return Dependency(
            key=key,
            provide=provide,
            dependencies=[cls._create_dependency_graph(key=k, dependencies=dependencies) for k in sub_dependency_keys],
        )

    @classmethod
    def _validate_dependency_data(
        cls,
        expected_form_data: Optional[Tuple[RequestEncodingType, ModelField]],
        dependency_kwargs_model: "KwargsModel",
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
        path_parameters: Set[str],
        dependencies: Dict[str, Provide],
        model_fields: Dict[str, ModelField],
        layered_parameters: Dict[str, ModelField],
    ) -> None:
        """Validate that there are no ambiguous kwargs, that is, kwargs declared using the same key in different
        places.
        """
        dependency_keys = set(dependencies.keys())

        parameter_names = {
            *(
                k
                for k, f in model_fields.items()
                if f.field_info.extra.get(ParamType.QUERY)
                or f.field_info.extra.get(ParamType.HEADER)
                or f.field_info.extra.get(ParamType.COOKIE)
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
