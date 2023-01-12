from functools import lru_cache
from http.cookies import _unquote as unquote_cookie
from typing import Any, Dict, Tuple
from urllib.parse import unquote

from fast_query_parsers import parse_query_string as fast_parse_query_string
from fast_query_parsers import parse_url_encoded_dict


@lru_cache(1024)
def parse_url_encoded_form_data(encoded_data: bytes) -> Dict[str, Any]:
    """Parse an url encoded form data dict.

    Args:
        encoded_data: The encoded byte string.

    Returns:
        A parsed dict.
    """
    return parse_url_encoded_dict(encoded_data)


@lru_cache(1024)
def parse_query_string(query_string: bytes) -> Tuple[Tuple[str, Any], ...]:
    """Parse a query string into a tuple of key value pairs.

    Args:
        query_string: A query string.
        encoding: The encoding to use.

    Returns:
        A tuple of key value pairs.
    """
    _bools = {"true": True, "false": False, "True": True, "False": False}
    return tuple((k, v if v not in _bools else _bools[v]) for k, v in fast_parse_query_string(query_string, "&"))


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
def parse_headers(headers: Tuple[Tuple[bytes, bytes], ...]) -> Dict[str, str]:
    """Parse ASGI headers into a dict of string keys and values.

    Args:
        headers: A tuple of bytes two tuples.

    Returns:
        A string / string dict.
    """
    return {k.decode(): v.decode() for k, v in headers}
