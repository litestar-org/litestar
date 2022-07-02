from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple, Union, cast

from pydantic.fields import ModelField, Undefined
from typing_extensions import Type

from starlite.connection import Request, WebSocket
from starlite.constants import RESERVED_KWARGS
from starlite.enums import RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException, ValidationException
from starlite.parsers import parse_form_data
from starlite.provide import Provide
from starlite.signature import SignatureModel, get_signature_model
from starlite.types import ReservedKwargs


class ParameterDefinition(NamedTuple):
    field_name: str
    field_alias: str
    is_required: bool
    default_value: Any


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
    This class is used to model the required kwargs for a given handler and its dependencies. This done during
    application bootstrap, to reduce the computation required during run-time.
    """

    __slots__ = (
        "expected_cookie_params",
        "expected_dependencies",
        "expected_form_data",
        "expected_header_params",
        "expected_path_params",
        "expected_query_params",
        "expected_reserved_kwargs",
    )

    def __init__(
        self,
        *,
        expected_dependencies: Set[Dependency],
        expected_form_data: Optional[Tuple[RequestEncodingType, ModelField]],
        expected_cookie_params: Set[ParameterDefinition],
        expected_header_params: Set[ParameterDefinition],
        expected_path_params: Set[ParameterDefinition],
        expected_query_params: Set[ParameterDefinition],
        expected_reserved_kwargs: Set[ReservedKwargs],
    ) -> None:
        self.expected_dependencies = expected_dependencies
        self.expected_form_data = expected_form_data
        self.expected_cookie_params = expected_cookie_params
        self.expected_header_params = expected_header_params
        self.expected_path_params = expected_path_params
        self.expected_query_params = expected_query_params
        self.expected_reserved_kwargs = expected_reserved_kwargs

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

    @classmethod
    def create_for_signature_model(
        cls, signature_model: Type[SignatureModel], dependencies: Dict[str, Provide], path_parameters: Set[str]
    ) -> "KwargsModel":
        """
        This function pre-determines what parameters are required for a given combination of route + route handler.

        This function executes for each Route+RouteHandler during the application bootstrap process.
        """
        cls.validate_raw_kwargs(
            path_parameters=path_parameters, dependencies=dependencies, model_fields=signature_model.__fields__
        )
        expected_reserved_kwargs = {
            field_name for field_name in signature_model.__fields__ if field_name in RESERVED_KWARGS
        }
        expected_dependencies: Set[Dependency] = {
            cls.create_dependency_graph(key=key, dependencies=dependencies)
            for key in dependencies
            if key in signature_model.__fields__
        }
        expected_path_parameters: Set[ParameterDefinition] = set()
        expected_header_parameters: Set[ParameterDefinition] = set()
        expected_cookie_parameters: Set[ParameterDefinition] = set()
        expected_query_parameters: Set[ParameterDefinition] = set()

        ignored_keys = {*RESERVED_KWARGS, *[dependency.key for dependency in expected_dependencies]}
        fields = filter(lambda keys: keys[0] not in ignored_keys, signature_model.__fields__.items())

        for field_name, model_field in fields:
            model_info = model_field.field_info
            extra_keys = set(model_info.extra)
            default = model_field.default if model_field.default is not Undefined else None
            is_required = model_info.extra.get("required", True)
            if field_name in path_parameters:
                parameter_set = expected_path_parameters
                field_alias = field_name
            elif "header" in extra_keys and model_info.extra["header"]:
                parameter_set = expected_header_parameters
                field_alias = model_info.extra["header"]
            elif "cookie" in extra_keys and model_info.extra["cookie"]:
                parameter_set = expected_cookie_parameters
                field_alias = model_info.extra["cookie"]
            else:
                parameter_set = expected_query_parameters
                field_alias = model_info.extra.get("query") or field_name
            parameter_set.add(
                ParameterDefinition(
                    field_name=field_name,
                    field_alias=field_alias,
                    default_value=default,
                    is_required=is_required and default is None and not model_field.allow_none,
                )
            )

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
            expected_reserved_kwargs=cast(Set[ReservedKwargs], expected_reserved_kwargs),
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
        cls, path_parameters: Set[str], dependencies: Dict[str, Provide], model_fields: Dict[str, ModelField]
    ) -> None:
        """
        Validates that there are no ambiguous kwargs, that is, kwargs declared using the same key in different places
        """
        aliased_parameters = {
            k
            for k, f in model_fields.items()
            if f.field_info.extra.get("query") or f.field_info.extra.get("header") or f.field_info.extra.get("cookie")
        }
        dependency_keys = set(dependencies.keys())

        for intersection in [
            path_parameters.intersection(dependency_keys)
            or path_parameters.intersection(aliased_parameters)
            or dependency_keys.intersection(aliased_parameters)
        ]:
            if intersection:
                raise ImproperlyConfiguredException(
                    f"Kwarg resolution ambiguity detected for the following keys: {', '.join(intersection)}. "
                    f"Make sure to use distinct keys for your dependencies, path parameters and aliased parameters."
                )

        used_reserved_kwargs = {*aliased_parameters, *path_parameters, *dependency_keys}.intersection(
            set(RESERVED_KWARGS)
        )
        if used_reserved_kwargs:
            raise ImproperlyConfiguredException(
                f"Reserved kwargs ({', '.join(RESERVED_KWARGS)}) cannot be used for dependencies and parameter "
                f"arguments. The following kwargs have been used by dependencies or aliased parameters: "
                f"{', '.join(used_reserved_kwargs)}"
            )

    def to_kwargs(self, connection: Union[WebSocket, Request]) -> Dict[str, Any]:
        """
        Return a dictionary of kwargs. Async values, i.e. CoRoutines, are not resolved to ensure this function is sync.
        """
        reserved_kwargs: Dict[str, Any] = {}
        if self.expected_reserved_kwargs:
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
                reserved_kwargs["data"] = self.get_request_data(request=cast(Request, connection))
        try:
            path_params = {
                field_name: connection.path_params[field_alias]
                if is_required
                else connection.path_params.get(field_alias, default)
                for field_name, field_alias, is_required, default in self.expected_path_params
            }
            query_params = {
                field_name: connection.query_params[field_alias]
                if is_required
                else connection.query_params.get(field_alias, default)
                for field_name, field_alias, is_required, default in self.expected_query_params
            }
            header_params = {
                field_name: connection.headers[field_alias]
                if is_required
                else connection.headers.get(field_alias, default)
                for field_name, field_alias, is_required, default in self.expected_header_params
            }
            cookie_params = {
                field_name: connection.cookies[field_alias]
                if is_required
                else connection.cookies.get(field_alias, default)
                for field_name, field_alias, is_required, default in self.expected_cookie_params
            }
            return {**reserved_kwargs, **path_params, **query_params, **header_params, **cookie_params}
        except KeyError as e:
            raise ValidationException(f"Missing required parameter {e.args[0]} for url {connection.url}") from e

    async def get_request_data(self, request: Request) -> Any:
        """
        Retrieves the data - either json data or form data - from the request
        """
        if self.expected_form_data:
            media_type, model_field = self.expected_form_data
            form_data = await request.form()
            return parse_form_data(media_type=media_type, form_data=form_data, field=model_field)
        return await request.json()

    async def resolve_dependency(
        self, dependency: Dependency, connection: Union[WebSocket, Request], **kwargs: Any
    ) -> Any:
        """
        Recursively resolve a dependency graph
        """
        signature_model = get_signature_model(dependency.provide)
        for sub_dependency in dependency.dependencies:
            kwargs[sub_dependency.key] = await self.resolve_dependency(
                dependency=sub_dependency, connection=connection, **kwargs
            )
        dependency_kwargs = signature_model.parse_values_from_connection_kwargs(connection=connection, **kwargs)
        return await dependency.provide(**dependency_kwargs)
