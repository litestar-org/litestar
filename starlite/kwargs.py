from collections import defaultdict
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from pydantic.fields import (
    SHAPE_DEQUE,
    SHAPE_FROZENSET,
    SHAPE_LIST,
    SHAPE_SEQUENCE,
    SHAPE_SET,
    SHAPE_TUPLE,
    SHAPE_TUPLE_ELLIPSIS,
    FieldInfo,
    ModelField,
    Undefined,
)
from pydantic_factories.utils import is_optional

from starlite.constants import (
    EXTRA_KEY_IS_PARAMETER,
    EXTRA_KEY_REQUIRED,
    RESERVED_KWARGS,
)
from starlite.datastructures.provide import Provide
from starlite.enums import ParamType, RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.parsers import parse_form_data, parse_query_string
from starlite.signature import SignatureModel, get_signature_model
from starlite.types import Empty

if TYPE_CHECKING:
    from starlite.connection import Request, WebSocket
    from starlite.types import ReservedKwargs


class ParameterDefinition(NamedTuple):
    """Tuple defining a kwarg representing a request parameter."""

    default_value: Any
    field_alias: str
    field_name: str
    is_required: bool
    is_sequence: bool
    param_type: ParamType


class Dependency:
    """Dependency graph of a given combination of `Route` + `RouteHandler`"""

    __slots__ = ("key", "provide", "dependencies")

    def __init__(self, key: str, provide: Provide, dependencies: List["Dependency"]) -> None:
        """Initialize a dependency.

        Args:
            key: The dependency key
            provide: Provider
            dependencies: List of child nodes
        """
        self.key = key
        self.provide = provide
        self.dependencies = dependencies


def merge_parameter_sets(first: Set[ParameterDefinition], second: Set[ParameterDefinition]) -> Set[ParameterDefinition]:
    """Given two sets of parameter definitions, coming from different dependencies for example, merge them into a single
    set.
    """
    result: Set[ParameterDefinition] = first.intersection(second)
    difference = first.symmetric_difference(second)
    for param in difference:
        # add the param if it's either required or no-other param in difference is the same but required
        if param.is_required or not any(p.field_alias == param.field_alias and p.is_required for p in difference):
            result.add(param)
    return result


def create_connection_value_extractor(
    connection_key: str,
    expected_params: Set[ParameterDefinition],
    parser: Optional[Callable[[Union["WebSocket", "Request"]], Dict[str, Any]]] = None,
) -> Callable[[Dict[str, Any], Union["WebSocket", "Request"]], None]:
    """Create a kwargs extractor function.

    Args:
        connection_key: The attribute key to use.
        expected_params: The set of expected params.
        parser: An optional parser function.

    Returns:
        An extractor function.
    """

    alias_and_key_tuple = tuple(
        (p.field_alias.lower() if p.param_type == ParamType.HEADER else p.field_alias, p.field_name)
        for p in expected_params
    )
    alias_defaults = {
        p.field_alias.lower() if p.param_type == ParamType.HEADER else p.field_alias: p.default_value
        for p in expected_params
        if not (p.is_required or p.default_value is Ellipsis)
    }

    def extractor(values: Dict[str, Any], connection: Union["WebSocket", "Request"]) -> None:
        data = parser(connection) if parser else getattr(connection, connection_key, {})

        try:
            connection_mapping: Dict[str, Any] = {
                key: data[alias] if alias in data else alias_defaults[alias] for alias, key in alias_and_key_tuple
            }
            values.update(connection_mapping)
        except KeyError as e:
            raise ValidationException(f"Missing required parameter {e.args[0]} for url {connection.url}") from e

    return extractor


@lru_cache
def create_query_default_dict(
    parsed_query: Tuple[Tuple[str, str], ...], sequence_query_parameter_names: Tuple[str, ...]
) -> DefaultDict[str, Union[List[str], str]]:
    """Transform a list of tuples into a default dict. Ensures non-list values are not wrapped in a list.

    Args:
        parsed_query: The parsed query list of tuples.
        sequence_query_parameter_names: A set of query parameters that should be wrapped in list.

    Returns:
        A default dict
    """
    output: DefaultDict[str, Union[List[str], str]] = defaultdict(list)

    for k, v in parsed_query:
        if k in sequence_query_parameter_names:
            output[k].append(v)  # type: ignore
        else:
            output[k] = v

    return output


class KwargsModel:
    """Model required kwargs for a given RouteHandler and its dependencies.

    This is done once and is memoized during application bootstrap, ensuring minimal runtime overhead.
    """

    __slots__ = (
        "expected_cookie_params",
        "expected_dependencies",
        "expected_form_data",
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
            expected_dependencies:  Any expected dependency kwargs
            expected_form_data: Any expected form data kwargs
            expected_header_params: Any expected header parameter kwargs
            expected_path_params: Any expected path parameter kwargs
            expected_query_params:  Any expected query parameter kwargs
            expected_reserved_kwargs: Any expected reserved kwargs, e.g. 'state'
            sequence_query_parameter_names: Any query parameters that are sequences
            is_data_optional: Treat data as optional
        """
        self.expected_cookie_params = expected_cookie_params
        self.expected_dependencies = expected_dependencies
        self.expected_form_data = expected_form_data
        self.expected_header_params = expected_header_params
        self.expected_path_params = expected_path_params
        self.expected_query_params = expected_query_params
        self.expected_reserved_kwargs = expected_reserved_kwargs
        self.sequence_query_parameter_names = tuple(sequence_query_parameter_names)

        self.has_kwargs = (
            expected_cookie_params
            or expected_dependencies
            or expected_form_data
            or expected_header_params
            or expected_path_params
            or expected_query_params
            or expected_reserved_kwargs
        )

        self.is_data_optional = is_data_optional
        self.extractors = self._create_extractors()

    def _create_extractors(self) -> List[Callable[[Dict[str, Any], Union["WebSocket", "Request"]], None]]:
        extractors: List[Callable[[Dict[str, Any], Union["WebSocket", "Request"]], None]] = []
        if self.expected_header_params:
            extractors.append(
                create_connection_value_extractor(
                    connection_key="headers", expected_params=self.expected_header_params
                ),
            )
        if self.expected_path_params:
            extractors.append(
                create_connection_value_extractor(
                    connection_key="path_params", expected_params=self.expected_path_params
                ),
            )
        if self.expected_cookie_params:
            extractors.append(
                create_connection_value_extractor(
                    connection_key="cookies", expected_params=self.expected_cookie_params
                ),
            )
        if self.expected_query_params:
            extractors.append(
                create_connection_value_extractor(
                    connection_key="query_params",
                    expected_params=self.expected_query_params,
                    parser=self._parse_connection_query_params,
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
    ) -> Tuple[Set[ParameterDefinition], set]:
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
                cls._create_parameter_definition(
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
                cls._create_parameter_definition(
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
                cls._create_parameter_definition(
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
        sequence_query_parameter_names = {
            p.field_alias for p in param_definitions if p.param_type == ParamType.QUERY and p.is_sequence
        }

        expected_form_data = None
        data_model_field = signature_model.__fields__.get("data")
        if data_model_field:
            media_type = data_model_field.field_info.extra.get("media_type")
            if media_type in (
                RequestEncodingType.MULTI_PART,
                RequestEncodingType.URL_ENCODED,
            ):
                expected_form_data = (media_type, data_model_field)

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

        return KwargsModel(
            expected_form_data=expected_form_data,  # pyright: ignore
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

    def _collect_reserved_kwargs(self, connection: Union["WebSocket", "Request"]) -> Dict[str, Any]:
        """Create and populate dictionary of "reserved" keyword arguments.

        Args:
            connection: An instance of [Request][starlite.connection.Request] or [WebSocket][starlite.connection.WebSocket].

        Returns:
            A dictionary of values correlating to reserved kwargs.
        """
        reserved_kwargs: Dict[str, Any] = {}
        if "state" in self.expected_reserved_kwargs:
            reserved_kwargs["state"] = connection.app.state.copy()
        if "headers" in self.expected_reserved_kwargs:
            reserved_kwargs["headers"] = connection.headers
        if "cookies" in self.expected_reserved_kwargs:
            reserved_kwargs["cookies"] = connection.cookies
        if "query" in self.expected_reserved_kwargs:
            reserved_kwargs["query"] = connection.query_params
        if "request" in self.expected_reserved_kwargs:
            reserved_kwargs["request"] = connection
        if "socket" in self.expected_reserved_kwargs:
            reserved_kwargs["socket"] = connection
        if "data" in self.expected_reserved_kwargs:
            reserved_kwargs["data"] = self._get_request_data(request=cast("Request", connection))
        if "scope" in self.expected_reserved_kwargs:
            reserved_kwargs["scope"] = connection.scope
        return reserved_kwargs

    def _parse_connection_query_params(self, connection: Union["WebSocket", "Request"]) -> Dict[str, Any]:
        """Parse query params and cache the result in scope.

        Args:
            connection: The ASGI connection instance.

        Returns:
            A dictionary of parsed values.
        """
        parsed_query = connection.scope["_parsed_query"] = (  # type: ignore
            connection._parsed_query  # pylint: disable=protected-access
            if connection._parsed_query is not Empty  # pylint: disable=protected-access
            else parse_query_string(connection.scope.get("query_string", b""))
        )
        return create_query_default_dict(
            parsed_query=parsed_query, sequence_query_parameter_names=self.sequence_query_parameter_names
        )

    def to_kwargs(self, connection: Union["WebSocket", "Request"]) -> Dict[str, Any]:
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

        if self.expected_reserved_kwargs:
            output.update(self._collect_reserved_kwargs(connection=connection))

        return output

    async def resolve_dependency(
        self, dependency: "Dependency", connection: Union["WebSocket", "Request"], **kwargs: Any
    ) -> Any:
        """Given an instance of [Dependency][starlite.kwargs.Dependency], recursively resolves its dependency graph.

        Args:
            dependency: An instance of [Dependency][starlite.kwargs.Dependency]
            connection: An instance of [Request][starlite.connection.Request] or [WebSocket][starlite.connection.WebSocket].
            **kwargs: Any kwargs to pass recursively.

        Returns:
            The resolved dependency value
        """
        signature_model = get_signature_model(dependency.provide)
        for sub_dependency in dependency.dependencies:
            kwargs[sub_dependency.key] = await self.resolve_dependency(
                dependency=sub_dependency, connection=connection, **kwargs
            )
        dependency_kwargs = signature_model.parse_values_from_connection_kwargs(connection=connection, **kwargs)
        return await dependency.provide(**dependency_kwargs)

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

    @staticmethod
    def _create_parameter_definition(
        allow_none: bool, field_info: FieldInfo, field_name: str, path_parameters: Set[str], is_sequence: bool
    ) -> ParameterDefinition:
        """Create a ParameterDefinition for the given pydantic FieldInfo instance and inserts it into the correct
        parameter set.
        """
        extra = field_info.extra
        is_required = extra.get(EXTRA_KEY_REQUIRED, True)
        default_value = field_info.default if field_info.default is not Undefined else None

        field_alias = extra.get(ParamType.QUERY) or field_name
        param_type = ParamType.QUERY

        if field_name in path_parameters:
            field_alias = field_name
            param_type = ParamType.PATH
        elif extra.get(ParamType.HEADER):
            field_alias = extra[ParamType.HEADER]
            param_type = ParamType.HEADER
        elif extra.get(ParamType.COOKIE):
            field_alias = extra[ParamType.COOKIE]
            param_type = ParamType.COOKIE

        return ParameterDefinition(
            param_type=param_type,
            field_name=field_name,
            field_alias=field_alias,
            default_value=default_value,
            is_required=is_required and (default_value is None and not allow_none),
            is_sequence=is_sequence,
        )

    @classmethod
    def _validate_dependency_data(
        cls,
        expected_form_data: Optional[Tuple[RequestEncodingType, ModelField]],
        dependency_kwargs_model: "KwargsModel",
    ) -> None:
        """Validate that the 'data' kwarg is compatible across dependencies."""
        if (expected_form_data and not dependency_kwargs_model.expected_form_data) or (
            not expected_form_data and dependency_kwargs_model.expected_form_data
        ):
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

    async def _get_request_data(self, request: "Request") -> Any:
        """Retrieve the data - either json data or form data - from the request"""
        if self.expected_form_data:
            media_type, model_field = self.expected_form_data
            form_data = await request.form()
            parsed_form = parse_form_data(media_type=media_type, form_data=form_data, field=model_field)
            return parsed_form if parsed_form or not self.is_data_optional else None
        return await request.json()
