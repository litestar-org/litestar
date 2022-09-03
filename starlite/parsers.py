from contextlib import suppress
from functools import reduce
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, cast
from urllib.parse import parse_qsl

from orjson import JSONDecodeError, loads
from pydantic.fields import SHAPE_LIST, SHAPE_SINGLETON
from starlette.datastructures import UploadFile as StarletteUploadFile

from starlite.datastructures import UploadFile
from starlite.enums import RequestEncodingType

if TYPE_CHECKING:
    from typing import Union

    from pydantic.fields import ModelField
    from starlette.datastructures import FormData
    from starlette.requests import HTTPConnection

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


def parse_query_params(connection: "HTTPConnection") -> Dict[str, Any]:
    """Parses and normalize a given connection's query parameters into a
    regular dictionary."""
    query_string = cast("Union[str, bytes]", connection.scope.get("query_string", ""))

    return reduce(
        _query_param_reducer,
        parse_qsl(
            query_string if isinstance(query_string, str) else query_string.decode("latin-1"), keep_blank_values=True
        ),
        {},
    )


def parse_form_data(media_type: "RequestEncodingType", form_data: "FormData", field: "ModelField") -> Any:
    """Transforms the multidict into a regular dict, try to load json on all
    non-file values.

    Supports lists.
    """
    values_dict: Dict[str, Any] = {}
    for key, value in form_data.multi_items():
        if not isinstance(value, (UploadFile, StarletteUploadFile)):
            with suppress(JSONDecodeError):
                value = loads(value)
        if isinstance(value, StarletteUploadFile) and not isinstance(value, UploadFile):
            value = UploadFile(
                filename=value.filename, file=value.file, content_type=value.content_type, headers=value.headers
            )
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
        if field.shape is SHAPE_SINGLETON and field.type_ in [UploadFile, StarletteUploadFile] and values_dict:
            return list(values_dict.values())[0]
    return values_dict
