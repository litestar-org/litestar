from contextlib import suppress
from functools import reduce
from typing import TYPE_CHECKING, Any, Dict, List, Tuple
from urllib.parse import parse_qsl

from orjson import JSONDecodeError, loads
from pydantic.fields import SHAPE_LIST, SHAPE_SINGLETON
from starlite_multipart.datastructures import UploadFile as MultipartUploadFile

from starlite.datastructures.upload_file import UploadFile
from starlite.enums import RequestEncodingType

if TYPE_CHECKING:

    from pydantic.fields import ModelField

    from starlite.datastructures.form_multi_dict import FormMultiDict

_true_values = {"True", "true"}
_false_values = {"False", "false"}


def _query_param_reducer(acc: Dict[str, List[Any]], cur: Tuple[str, str]) -> Dict[str, List[str]]:
    """
    Reducer function - acc is a dictionary, cur is a tuple of key + value

    We use reduce because python implements reduce in C, which makes it faster than a regular for loop in most cases.
    """
    key, value = cur

    if value in _true_values:
        value = True  # type: ignore
    elif value in _false_values:
        value = False  # type: ignore

    if key in acc:
        acc[key].append(value)
    else:
        acc[key] = [value]
    return acc


def parse_query_params(query_string: bytes) -> Dict[str, List[str]]:
    """Parses and normalize a given connection's query parameters into a
    regular dictionary.

    Args:
        query_string: A byte-string containing a query

    Returns:
        A string keyed dictionary of values.
    """

    return reduce(_query_param_reducer, parse_qsl(query_string.decode("utf-8"), keep_blank_values=True), {})


def parse_form_data(media_type: "RequestEncodingType", form_data: "FormMultiDict", field: "ModelField") -> Any:
    """Transforms the multidict into a regular dict, try to load json on all
    non-file values.

    Supports lists.
    """
    values_dict: Dict[str, Any] = {}
    for key, value in form_data.multi_items():
        if not isinstance(value, MultipartUploadFile):
            with suppress(JSONDecodeError):
                value = loads(value)
        existing_value = values_dict.get(key)
        if isinstance(existing_value, list):
            values_dict[key].append(value)
        elif existing_value:
            values_dict[key] = [existing_value, value]
        else:
            values_dict[key] = value
    if media_type == RequestEncodingType.MULTI_PART:
        if field.shape is SHAPE_LIST:
            return list(values_dict.values())
        if field.shape is SHAPE_SINGLETON and field.type_ in (UploadFile, MultipartUploadFile) and values_dict:
            return list(values_dict.values())[0]
    return values_dict
