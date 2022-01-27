from functools import reduce
from typing import Any, Dict, List, Tuple, Union, cast
from urllib.parse import parse_qsl

from starlette.requests import HTTPConnection
from typing_extensions import Type

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
    try:
        qs = cast(Union[str, bytes], connection.scope["query_string"])
        return reduce(
            _query_param_reducer,
            parse_qsl(qs if isinstance(qs, str) else qs.decode("latin-1"), keep_blank_values=True),
            {},
        )
    except KeyError:
        return {}


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
