from __future__ import annotations

from functools import lru_cache
from http.cookies import _unquote as unquote_cookie
from typing import Any, Iterable
from urllib.parse import unquote

from fast_query_parsers import parse_query_string as fast_parse_query_string
from fast_query_parsers import parse_url_encoded_dict

__all__ = ("parse_cookie_string", "parse_headers", "parse_query_string", "parse_url_encoded_form_data")


@lru_cache(1024)
def parse_url_encoded_form_data(encoded_data: bytes) -> dict[str, Any]:
    """Parse an url encoded form data dict.

    Args:
        encoded_data: The encoded byte string.

    Returns:
        A parsed dict.
    """
    return parse_url_encoded_dict(qs=encoded_data, parse_numbers=False)


@lru_cache(1024)
def parse_query_string(query_string: bytes) -> tuple[tuple[str, Any], ...]:
    """Parse a query string into a tuple of key value pairs.

    Args:
        query_string: A query string.

    Returns:
        A tuple of key value pairs.
    """
    return tuple(fast_parse_query_string(query_string, "&"))


@lru_cache(1024)
def parse_cookie_string(cookie_string: str) -> dict[str, str]:
    """Parse a cookie string into a dictionary of values.

    Args:
        cookie_string: A cookie string.

    Returns:
        A string keyed dictionary of values
    """
    cookies = [cookie.split("=", 1) if "=" in cookie else ("", cookie) for cookie in cookie_string.split(";")]
    output: dict[str, str] = {
        k: unquote(unquote_cookie(v))
        for k, v in filter(
            lambda x: x[0] or x[1],
            ((k.strip(), v.strip()) for k, v in cookies),
        )
    }
    return output


@lru_cache(1024)
def _parse_headers(headers: tuple[tuple[bytes, bytes], ...]) -> dict[str, str]:
    """Parse ASGI headers into a dict of string keys and values.

    Args:
        headers: A tuple of bytes two tuples.

    Returns:
        A string / string dict.
    """
    return {k.decode(): v.decode() for k, v in headers}


def parse_headers(headers: Iterable[tuple[bytes, bytes] | list[bytes]]) -> dict[str, str]:
    """Parse ASGI headers into a dict of string keys and values.

    Since the ASGI protocol only allows for lists (not tuples) which cannot be hashed,
    this function will convert the headers to a tuple of tuples before invoking the cached function.
    """
    return _parse_headers(tuple(tuple(h) for h in headers))
