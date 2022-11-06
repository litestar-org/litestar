from contextlib import suppress
from http.cookies import _unquote as unquote_cookie
from typing import TYPE_CHECKING, Any, Dict
from urllib.parse import unquote

from orjson import JSONDecodeError, loads
from pydantic.fields import SHAPE_LIST, SHAPE_SINGLETON
from starlite_multipart.datastructures import UploadFile as MultipartUploadFile

from starlite.datastructures.upload_file import UploadFile
from starlite.enums import RequestEncodingType

if TYPE_CHECKING:

    from pydantic.fields import ModelField

    from starlite.datastructures.multi_dicts import FormMultiDict

_true_values = {"True", "true"}
_false_values = {"False", "false"}


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


def parse_cookie_string(cookie_string: str) -> Dict[str, str]:
    """
    Parses a cookie string into a dictionary of values.
    Args:
        cookie_string: A cookie string.

    Returns:
        A string keyed dictionary of values
    """
    output: Dict[str, str] = {}
    cookies = [cookie.split("=", 1) if "=" in cookie else ("", cookie) for cookie in cookie_string.split(";")]
    for k, v in filter(lambda x: x[0] or x[1], ((k.strip(), v.strip()) for k, v in cookies)):
        output[k] = unquote(unquote_cookie(v))
    return output
