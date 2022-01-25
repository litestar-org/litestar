from inspect import isawaitable
from typing import NamedTuple, Any, Set, Tuple, Optional, Dict, cast, Union, List

from pydantic.fields import ModelField, Undefined

from starlite.enums import RequestEncodingType
from starlite.provide import Provide
from starlite.exceptions import  ImproperlyConfiguredException
from starlite.constants import RESERVED_FIELD_NAMES
from starlite.exceptions import ValidationException
from starlite.request import handle_multipart, WebSocket, Request
from starlite.signature import SignatureModel
from starlite.types import ReservedKwargs


class ParameterDefinition(NamedTuple):
    field_name: str
    field_alias: str
    is_required: bool
    default_value: Any


class Dependency:
    __slots__ = ("key", "provide", "dependencies")

    def __init__(self, key: str, provide: Provide, dependencies: List["Dependency"]):
        self.key = key
        self.provide = provide
        self.dependencies = dependencies


def merge_parameter_sets(first: Set[ParameterDefinition], second: Set[ParameterDefinition]):
    """
    Given two sets of parameter definitions, coming from different dependencies for example, merge them into a single set
    """
    result: Set[ParameterDefinition] = first.intersection(second)
    difference = first.symmetric_difference(second)
    for param in difference:
        if param.is_required:
            result.add(param)
        elif any(p != param and p.field_alias == param.field_alias and p.is_required for p in difference):
            continue
        else:
            result.add(param)
    return result


class KwargsModel:
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
        provide = dependencies[key]
        sub_dependency_keys = [k for k in cast(SignatureModel, provide.signature_model).__fields__ if k in dependencies]
        return Dependency(key=key, provide=provide,
                          dependencies=[cls.create_dependency_graph(key=k, dependencies=dependencies) for k in
                                        sub_dependency_keys])

    @classmethod
    def create_for_signature_model(
            cls, signature_model: SignatureModel, dependencies: Dict[str, Provide], path_parameters: Set[str]
    ) -> "KwargsModel":
        """
        This function pre-determines what parameters are required for a given combination of route + route handler.

        This function during the application bootstrap process, to ensure optimal runtime performance.
        """
        expected_reserved_kwargs = {
            field_name for field_name in signature_model.__fields__ if field_name in RESERVED_FIELD_NAMES
        }
        expected_dependencies: Set[Dependency] = {cls.create_dependency_graph(key=key, dependencies=dependencies) for key in dependencies if key in signature_model.__fields__}
        expected_path_parameters: Set[ParameterDefinition] = set()
        expected_header_parameters: Set[ParameterDefinition] = set()
        expected_cookie_parameters: Set[ParameterDefinition] = set()
        expected_query_parameters: Set[ParameterDefinition] = set()

        for dependency in expected_dependencies:
            if dependency.key in path_parameters:
                raise ImproperlyConfiguredException(
                    f"path parameter and dependency kwarg have a similar key - {dependency.key}"
                )
        for key in path_parameters:
            model_field = signature_model.__fields__.get(key)
            if model_field:
                default = model_field.default if model_field.default is not Undefined else None
                if model_field:
                    expected_path_parameters.add(
                        ParameterDefinition(
                            field_name=key,
                            field_alias=key,
                            default_value=default,
                            is_required=default is None and not model_field.allow_none and default is None,
                        )
                    )
        aliased_fields = set()
        for field_name, model_field in signature_model.__fields__.items():
            model_info = model_field.field_info
            extra_keys = set(model_info.extra)
            default = model_field.default if model_field.default is not Undefined else None
            is_required = model_info.extra.get("required")
            if "query" in extra_keys and model_info.extra["query"]:
                aliased_fields.add(field_name)
                field_alias = model_info.extra["query"]
                expected_query_parameters.add(
                    ParameterDefinition(
                        field_name=field_name,
                        field_alias=field_alias,
                        default_value=default,
                        is_required=is_required and default is None,
                    )
                )
            elif "header" in extra_keys and model_info.extra["header"]:
                aliased_fields.add(field_name)
                field_alias = model_info.extra["header"]
                expected_header_parameters.add(
                    ParameterDefinition(
                        field_name=field_name,
                        field_alias=field_alias,
                        default_value=default,
                        is_required=is_required and default is None,
                    )
                )
            elif "cookie" in extra_keys and model_info.extra["cookie"]:
                aliased_fields.add(field_name)
                field_alias = model_info.extra["cookie"]
                expected_cookie_parameters.add(
                    ParameterDefinition(
                        field_name=field_name,
                        field_alias=field_alias,
                        default_value=default,
                        is_required=is_required and default is None,
                    )
                )

        for key in set(signature_model.__fields__) - {
            *{dependency.key for dependency in expected_dependencies},
            *{param.field_name for param in expected_path_parameters},
            *expected_reserved_kwargs,
            *aliased_fields,
            "data",
        }:
            model_field = signature_model.__fields__[key]
            default = model_field.default if model_field.default is not Undefined else None
            expected_query_parameters.add(
                ParameterDefinition(
                    field_name=key,
                    field_alias=key,
                    default_value=default,
                    is_required=default is None and not model_field.allow_none and default is None,
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
            kwarg_model = cls.create_for_signature_model(
                signature_model=cast(SignatureModel, dependency.provide.signature_model),
                dependencies=dependencies,
                path_parameters=path_parameters,
            )
            expected_path_parameters = merge_parameter_sets(expected_path_parameters, kwarg_model.expected_path_params)
            expected_query_parameters = merge_parameter_sets(
                expected_query_parameters, kwarg_model.expected_query_params
            )
            expected_cookie_parameters = merge_parameter_sets(
                expected_cookie_parameters, kwarg_model.expected_cookie_params
            )
            expected_header_parameters = merge_parameter_sets(
                expected_header_parameters, kwarg_model.expected_header_params
            )

            if "data" in expected_reserved_kwargs and "data" in kwarg_model.expected_reserved_kwargs:
                if (expected_form_data and not kwarg_model.expected_form_data) or (
                        not expected_form_data and kwarg_model.expected_form_data
                ):
                    raise ImproperlyConfiguredException(
                        "Dependencies have incompatible 'data' kwarg types- one expects JSON and the other expects form data"
                    )
                if expected_form_data and kwarg_model.expected_form_data:
                    local_media_type, _ = expected_form_data
                    dependency_media_type, _ = kwarg_model.expected_form_data
                    if local_media_type != dependency_media_type:
                        raise ImproperlyConfiguredException(
                            "Dependencies have incompatible form data encoding - one expects url-encoded and the other expects multi-part"
                        )
            expected_reserved_kwargs.update(kwarg_model.expected_reserved_kwargs)
        return KwargsModel(
            expected_form_data=expected_form_data,
            expected_dependencies=expected_dependencies,
            expected_path_params=expected_path_parameters,
            expected_query_params=expected_query_parameters,
            expected_cookie_params=expected_cookie_parameters,
            expected_header_params=expected_header_parameters,
            expected_reserved_kwargs=expected_reserved_kwargs,
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
                reserved_kwargs["headers"] = dict(connection.headers)
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
        if self.expected_form_data:
            media_type, model_field = self.expected_form_data
            form_data = await request.form()
            return handle_multipart(media_type=media_type, form_data=form_data, field=model_field)
        return await request.json()

    async def resolve_dependency(self, dependency: Dependency, connection: Union[WebSocket, Request], **kwargs: Any) -> Any:
        """
        Recursively resolve a dependency graph
        """
        for sub_dependency in dependency.dependencies:
            kwargs[sub_dependency.key] = await self.resolve_dependency(dependency=sub_dependency, connection=connection, **kwargs)
        dependency_kwargs = dependency.provide.signature_model.parse_values_from_connection_kwargs(connection=connection, **kwargs)
        value = dependency.provide(**dependency_kwargs)
        if isawaitable(value):
            value = await value
        return value
