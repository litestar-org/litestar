from collections import defaultdict
from contextlib import suppress
from functools import lru_cache
from http.cookies import _unquote as unquote_cookie
from typing import Any, DefaultDict, Dict, List, Tuple
from urllib.parse import parse_qsl, unquote

from msgspec import DecodeError

from starlite.utils.serialization import decode_json


@lru_cache(1024)
def parse_cookie_string(cookie_string: str) -> Dict[str, str]:
    """Parse a cookie string into a dictionary of values.

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


@lru_cache(1024)
def parse_query_string(query_string: bytes, encoding: str = "utf-8") -> Tuple[Tuple[str, Any], ...]:
    """Parse a query string into a tuple of key value pairs.

    Args:
        query_string: A query string.
        encoding: The encoding to use.

    Returns:
        A tuple of key value pairs.
    """
    _bools = {b"true": True, b"false": False, b"True": True, b"False": False}
    return tuple(
        (k.decode(encoding), v.decode(encoding) if v not in _bools else _bools[v])
        for k, v in parse_qsl(query_string, keep_blank_values=True)
    )


@lru_cache(1024)
def parse_url_encoded_form_data(encoded_data: bytes, encoding: str) -> Dict[str, Any]:
    """Parse a url encoded form data dict.

    Args:
        encoded_data: The encoded byte string.
        encoding: The encoding used.

    Returns:
        A parsed dict.
    """
    decoded_dict: DefaultDict[str, List[Any]] = defaultdict(list)
    for k, v in parse_query_string(query_string=encoded_data, encoding=encoding):
        with suppress(DecodeError):
            v = decode_json(v) if isinstance(v, str) else v
        decoded_dict[k].append(v)
    return {k: v if len(v) > 1 else v[0] for k, v in decoded_dict.items()}


@lru_cache(1024)
def parse_headers(headers: Tuple[Tuple[bytes, bytes], ...]) -> Dict[str, str]:
    """Parse ASGI headers into a dict of string keys and values.

    Args:
        headers: A tuple of bytes two tuples.

    Returns:
        A string / string dict.
    """
    return {k.decode(): v.decode() for k, v in headers}
