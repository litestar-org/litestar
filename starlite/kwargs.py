from typing import (
    TYPE_CHECKING,
    Any,
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

from starlite.constants import (
    EXTRA_KEY_IS_PARAMETER,
    EXTRA_KEY_REQUIRED,
    RESERVED_KWARGS,
)
from starlite.enums import ParamType, RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.parsers import parse_form_data
from starlite.provide import Provide
from starlite.signature import SignatureModel, get_signature_model

if TYPE_CHECKING:
    from starlite.connection import Request, WebSocket
    from starlite.types import ReservedKwargs

# Shapes corresponding to sequences
SEQ_SHAPES = {
    SHAPE_LIST,
    SHAPE_SET,
    SHAPE_SEQUENCE,
    SHAPE_TUPLE,
    SHAPE_TUPLE_ELLIPSIS,
    SHAPE_DEQUE,
    SHAPE_FROZENSET,
}


class ParameterDefinition(NamedTuple):
    param_type: ParamType
    field_name: str
    field_alias: str
    is_required: bool
    default_value: Any
    is_sequence: bool


class Dependency:
    """
    This class is used to create a dependency graph for a given combination of Route + RouteHandler
    """

    __slots__ = ("key", "provide", "dependencies")

    def __init__(self, key: str, provide: Provide, dependencies: List["Dependency"]) -> None:
        self.key = key
        self.provide = provide
        self.dependencies = dependencies


def merge_parameter_sets(first: Set[ParameterDefinition], second: Set[ParameterDefinition]) -> Set[ParameterDefinition]:
    """
    Given two sets of parameter definitions, coming from different dependencies for example, merge them into a single set
    """
    result: Set[ParameterDefinition] = first.intersection(second)
    difference = first.symmetric_difference(second)
    for param in difference:
        # add the param if it's either required or no-other param in difference is the same but required
        if param.is_required or not any(p.field_alias == param.field_alias and p.is_required for p in difference):
            result.add(param)
    return result


class KwargsModel:
    """
    This class is used to model the required kwargs for a given handler and its dependencies.
    This is done once and is cached during application bootstrap, ensuring minimal runtime overhead.
    """

    __slots__ = (
        "has_kwargs",
        "expected_cookie_params",
        "expected_dependencies",
        "expected_form_data",
        "expected_header_params",
        "expected_path_params",
        "expected_query_params",
        "expected_reserved_kwargs",
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
    ) -> None:
        self.expected_cookie_params = expected_cookie_params
        self.expected_dependencies = expected_dependencies
        self.expected_form_data = expected_form_data
        self.expected_header_params = expected_header_params
        self.expected_path_params = expected_path_params
        self.expected_query_params = expected_query_params
        self.expected_reserved_kwargs = expected_reserved_kwargs
        self.sequence_query_parameter_names = sequence_query_parameter_names
        self.has_kwargs = (
            expected_cookie_params
            or expected_dependencies
            or expected_form_data
            or expected_header_params
            or expected_path_params
            or expected_query_params
            or expected_reserved_kwargs
        )

    @classmethod
    def create_dependency_graph(cls, key: str, dependencies: Dict[str, Provide]) -> Dependency:
        """
        Creates a graph like structure of dependencies, with each dependency including its own dependencies as a list.
        """
        provide = dependencies[key]
        sub_dependency_keys = [k for k in get_signature_model(provide).__fields__ if k in dependencies]
        return Dependency(
            key=key,
            provide=provide,
            dependencies=[cls.create_dependency_graph(key=k, dependencies=dependencies) for k in sub_dependency_keys],
        )

    @staticmethod
    def create_parameter_definition(
        allow_none: bool, field_info: FieldInfo, field_name: str, path_parameters: Set[str], is_sequence: bool
    ) -> ParameterDefinition:
        """
        Creates a ParameterDefinition for the given pydantic FieldInfo instance and inserts it into the correct parameter set
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
    def create_for_signature_model(
        cls,
        signature_model: Type[SignatureModel],
        dependencies: Dict[str, Provide],
        path_parameters: Set[str],
        layered_parameters: Dict[str, ModelField],
    ) -> "KwargsModel":
        """
        This function pre-determines what parameters are required for a given combination of route + route handler.
        It is executed during the application bootstrap process.
        """

        cls.validate_raw_kwargs(
            path_parameters=path_parameters,
            dependencies=dependencies,
            model_fields=signature_model.__fields__,
            layered_parameters=layered_parameters,
        )
        expected_reserved_kwargs = {
            field_name for field_name in signature_model.__fields__ if field_name in RESERVED_KWARGS
        }
        expected_dependencies = {
            cls.create_dependency_graph(key=key, dependencies=dependencies)
            for key in dependencies
            if key in signature_model.__fields__
        }

        ignored_keys = {*RESERVED_KWARGS, *(dependency.key for dependency in expected_dependencies)}

        param_definitions = {
            *(
                cls.create_parameter_definition(
                    allow_none=model_field.allow_none,
                    field_name=field_name,
                    field_info=model_field.field_info,
                    path_parameters=path_parameters,
                    is_sequence=model_field.shape in SEQ_SHAPES,
                )
                for field_name, model_field in layered_parameters.items()
                if field_name not in ignored_keys and field_name not in signature_model.__fields__
            ),
            *(
                cls.create_parameter_definition(
                    allow_none=model_field.allow_none,
                    field_name=field_name,
                    field_info=model_field.field_info,
                    path_parameters=path_parameters,
                    is_sequence=model_field.shape in SEQ_SHAPES,
                )
                for field_name, model_field in signature_model.__fields__.items()
                if field_name not in ignored_keys and field_name not in layered_parameters
            ),
        }

        for field_name, model_field in filter(
            lambda items: items[0] not in ignored_keys and items[0] in layered_parameters,
            signature_model.__fields__.items(),
        ):
            layer_field_info = layered_parameters[field_name].field_info
            signature_field_info = model_field.field_info

            field_info = layer_field_info
            # allow users to manually override Parameter definition using Parameter
            if signature_field_info.extra.get(EXTRA_KEY_IS_PARAMETER):
                field_info = signature_field_info

            field_info.default = (
                signature_field_info.default
                if signature_field_info.default not in [Undefined, Ellipsis]
                else layer_field_info.default
            )

            param_definitions.add(
                cls.create_parameter_definition(
                    allow_none=model_field.allow_none,
                    field_name=field_name,
                    field_info=field_info,
                    path_parameters=path_parameters,
                    is_sequence=model_field.shape in SEQ_SHAPES,
                )
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
            if media_type in [
                RequestEncodingType.MULTI_PART,
                RequestEncodingType.URL_ENCODED,
            ]:
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
                cls.validate_dependency_data(
                    expected_form_data=expected_form_data, dependency_kwargs_model=dependency_kwargs_model
                )
            expected_reserved_kwargs.update(dependency_kwargs_model.expected_reserved_kwargs)

        return KwargsModel(
            expected_form_data=expected_form_data,
            expected_dependencies=expected_dependencies,
            expected_path_params=expected_path_parameters,
            expected_query_params=expected_query_parameters,
            expected_cookie_params=expected_cookie_parameters,
            expected_header_params=expected_header_parameters,
            expected_reserved_kwargs=cast("Set[ReservedKwargs]", expected_reserved_kwargs),
            sequence_query_parameter_names=sequence_query_parameter_names,
        )

    @classmethod
    def validate_dependency_data(
        cls,
        expected_form_data: Optional[Tuple[RequestEncodingType, ModelField]],
        dependency_kwargs_model: "KwargsModel",
    ) -> None:
        """
        Validates that the 'data' kwarg is compatible across dependencies
        """
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
    def validate_raw_kwargs(
        cls,
        path_parameters: Set[str],
        dependencies: Dict[str, Provide],
        model_fields: Dict[str, ModelField],
        layered_parameters: Dict[str, ModelField],
    ) -> None:
        """
        Validates that there are no ambiguous kwargs, that is, kwargs declared using the same key in different places
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

        for intersection in [
            path_parameters.intersection(dependency_keys)
            or path_parameters.intersection(parameter_names)
            or dependency_keys.intersection(parameter_names)
        ]:
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

    def _sequence_or_scalar_param(self, key: str, value: List[str]) -> Union[str, List[str]]:
        """
        Returns the first element of 'value' if we expect it to be a scalar value (appears in self.sequence_query_parameter_names)
        and it contains only a single element.
        """
        return value[0] if key not in self.sequence_query_parameter_names and len(value) == 1 else value

    def to_kwargs(self, connection: Union["WebSocket", "Request"]) -> Dict[str, Any]:
        """
        Return a dictionary of kwargs. Async values, i.e. CoRoutines, are not resolved to ensure this function is sync.
        """
        reserved_kwargs: Dict[str, Any] = {}
        connection_query_params = {k: self._sequence_or_scalar_param(k, v) for k, v in connection.query_params.items()}
        if self.expected_reserved_kwargs:
            if "state" in self.expected_reserved_kwargs:
                reserved_kwargs["state"] = connection.app.state.copy()
            if "headers" in self.expected_reserved_kwargs:
                reserved_kwargs["headers"] = connection.headers
            if "cookies" in self.expected_reserved_kwargs:
                reserved_kwargs["cookies"] = connection.cookies
            if "query" in self.expected_reserved_kwargs:
                reserved_kwargs["query"] = connection_query_params
            if "request" in self.expected_reserved_kwargs:
                reserved_kwargs["request"] = connection
            if "socket" in self.expected_reserved_kwargs:
                reserved_kwargs["socket"] = connection
            if "data" in self.expected_reserved_kwargs:
                reserved_kwargs["data"] = self.get_request_data(request=cast("Request", connection))
        try:
            path_params = {
                param.field_name: connection.path_params[param.field_alias]
                if param.is_required
                else connection.path_params.get(param.field_alias, param.default_value)
                for param in self.expected_path_params
            }
            query_params = {
                param.field_name: connection_query_params[param.field_alias]
                if param.is_required
                else connection_query_params.get(param.field_alias, param.default_value)
                for param in self.expected_query_params
            }
            header_params = {
                param.field_name: connection.headers[param.field_alias]
                if param.is_required
                else connection.headers.get(param.field_alias, param.default_value)
                for param in self.expected_header_params
            }
            cookie_params = {
                param.field_name: connection.cookies[param.field_alias]
                if param.is_required
                else connection.cookies.get(param.field_alias, param.default_value)
                for param in self.expected_cookie_params
            }
            return {**reserved_kwargs, **path_params, **query_params, **header_params, **cookie_params}
        except KeyError as e:
            raise ValidationException(f"Missing required parameter {e.args[0]} for url {connection.url}") from e

    async def get_request_data(self, request: "Request") -> Any:
        """
        Retrieves the data - either json data or form data - from the request
        """
        if self.expected_form_data:
            media_type, model_field = self.expected_form_data
            form_data = await request.form()
            return parse_form_data(media_type=media_type, form_data=form_data, field=model_field)
        return await request.json()

    async def resolve_dependency(
        self, dependency: "Dependency", connection: Union["WebSocket", "Request"], **kwargs: Any
    ) -> Any:
        """
        Recursively resolves a dependency graph
        """
        signature_model = get_signature_model(dependency.provide)
        for sub_dependency in dependency.dependencies:
            kwargs[sub_dependency.key] = await self.resolve_dependency(
                dependency=sub_dependency, connection=connection, **kwargs
            )
        dependency_kwargs = signature_model.parse_values_from_connection_kwargs(connection=connection, **kwargs)
        return await dependency.provide(**dependency_kwargs)
