from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from http.cookies import _unquote as unquote_cookie
from typing import Iterable
from urllib.parse import unquote

try:
    from fast_query_parsers import parse_query_string as parse_qsl
except ImportError:
    from urllib.parse import parse_qsl as _parse_qsl

    def parse_qsl(qs: bytes, separator: str) -> list[tuple[str, str]]:
        return _parse_qsl(qs.decode("latin-1"), keep_blank_values=True, separator=separator)


__all__ = ("parse_cookie_string", "parse_headers", "parse_query_string", "parse_url_encoded_form_data")


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
