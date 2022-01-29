from contextlib import suppress
from functools import reduce
from typing import Any, Dict, List, Tuple, Union, cast
from urllib.parse import parse_qsl

from orjson import JSONDecodeError, loads
from pydantic.fields import SHAPE_LIST, SHAPE_SINGLETON, ModelField
from starlette.datastructures import FormData, UploadFile
from starlette.requests import HTTPConnection
from typing_extensions import Type

from starlite.enums import RequestEncodingType
from starlite.exceptions import ValidationException

_true_values = {"True", "true"}
_false_values = {"False", "false"}


def _query_param_reducer(
    acc: Dict[str, Union[str, List[str]]], cur: Tuple[str, str]
) -> Dict[str, Union[str, List[str]]]:
    """
    Reducer function - acc is a dictionary, cur is a tuple of key + value

    We use reduce because python implements reduce in C, which makes it faster than a regular for loop in most cases.
    """
    key, value = cur
    if value in _true_values:
        value = True  # type: ignore
    elif value in _false_values:
        value = False  # type: ignore
    param = acc.get(key)
    if param is None:
        acc[key] = value
    elif isinstance(param, str):
        acc[key] = [param, value]
    else:
        acc[key].append(value)  # type: ignore
    return acc


def parse_query_params(connection: HTTPConnection) -> Dict[str, Any]:
    """
    Parses and normalize a given connection's query parameters into a regular dictionary
    """
    qs = cast(Union[str, bytes], connection.scope.get("query_string", ""))
    return reduce(
        _query_param_reducer,
        parse_qsl(qs if isinstance(qs, str) else qs.decode("latin-1"), keep_blank_values=True),
        {},
    )


def _path_param_reducer(acc: Dict[str, Union[str, List[str]]], cur: Tuple[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    Reducer function - acc is a dictionary, cur is a tuple of a param definition object + raw string value
    """
    param_definition, raw_param = cur
    param_name = cast(str, param_definition["name"])
    param_type = cast(Type, param_definition["type"])
    acc[param_name] = param_type(raw_param)
    return acc


def parse_path_params(path_parameters: List[Dict[str, Any]], raw_params: List[str]) -> Dict[str, Any]:
    """
    Parses raw path parameters by mapping them into a dictionary
    """
    try:
        return reduce(_path_param_reducer, zip(path_parameters, raw_params), {})
    except (ValueError, TypeError, KeyError) as e:  # pragma: no cover
        raise ValidationException(f"unable to parse path parameters {str(raw_params)}") from e


def parse_form_data(media_type: RequestEncodingType, form_data: FormData, field: ModelField) -> Any:
    """
    Transforms the multidict into a regular dict, try to load json on all non-file values.

    Supports lists.
    """
    values_dict: Dict[str, Any] = {}
    for key, value in form_data.multi_items():
        if not isinstance(value, UploadFile):
            with suppress(JSONDecodeError):
                value = loads(value)
        if values_dict.get(key):
            if isinstance(values_dict[key], list):
                values_dict[key].append(value)
            else:
                values_dict[key] = [values_dict[key], value]
        else:
            values_dict[key] = value
    if media_type == RequestEncodingType.MULTI_PART:
        if field.shape is SHAPE_LIST:
            return list(values_dict.values())
        if field.shape is SHAPE_SINGLETON and field.type_ is UploadFile and values_dict:
            return list(values_dict.values())[0]
    return values_dict
