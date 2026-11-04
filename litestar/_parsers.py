from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from http.cookies import _unquote as unquote_cookie
from urllib.parse import parse_qsl as _parse_qsl
from urllib.parse import unquote


def parse_qsl(qs: bytes, separator: str) -> list[tuple[str, str]]:
    return _parse_qsl(qs.decode("latin-1"), keep_blank_values=True, separator=separator)


__all__ = ("parse_cookie_string", "parse_query_string", "parse_url_encoded_form_data")


@lru_cache(1024)
def parse_url_encoded_form_data(encoded_data: bytes) -> dict[str, str | list[str]]:
    """Parse an url encoded form data dict.

    Args:
        encoded_data: The encoded byte string.

    Returns:
        A parsed dict.
    """
    decoded_dict: defaultdict[str, list[str]] = defaultdict(list)
    for k, v in parse_qsl(encoded_data, separator="&"):
        decoded_dict[k].append(v)
    return {k: v if len(v) > 1 else v[0] for k, v in decoded_dict.items()}


@lru_cache(1024)
def parse_query_string(query_string: bytes) -> tuple[tuple[str, str], ...]:
    """Parse a query string into a tuple of key value pairs.

    Args:
        query_string: A query string.

    Returns:
        A tuple of key value pairs.
    """
    return tuple(parse_qsl(query_string, separator="&"))


@lru_cache(1024)
def parse_cookie_string(cookie_string: str) -> dict[str, str]:
    """Parse a cookie string into a dictionary of values.

    A name occurring more than once keeps its first value. For the ``Cookie`` header this
    name is sent in, :rfc:`6265` has a user agent serialise a cookie of a longer path
    first, so the first value is the one of the cookie scoped to the more specific path.
    Of two cookies of the same path, it is the one set first.

    Args:
        cookie_string: A cookie string.

    Returns:
        A string keyed dictionary of values
    """
    output: dict[str, str] = {}
    for cookie in cookie_string.split(";"):
        key, separator, value = cookie.partition("=")
        if not separator:
            key, value = "", key
        key, value = key.strip(), value.strip()
        if (key or value) and key not in output:
            output[key] = unquote(unquote_cookie(value))
    return output
