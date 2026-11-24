from __future__ import annotations

import difflib
import inspect
import reprlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar.di.provider import Provider


_bounded_repr = reprlib.Repr()
# The default of 30 cuts a function's repr in the middle of its qualified name.
_bounded_repr.maxother = 200


def _format_key(key: Any) -> str:
    if isinstance(key, str):
        return repr(key)
    return getattr(key, "__qualname__", None) or getattr(key, "__name__", None) or repr(key)


def _format_scope_chain(scopes: tuple[str, ...]) -> str:
    return " -> ".join(repr(scope) for scope in scopes)


def _describe_callable(fn: Any) -> str:
    """Best effort callable "name" description as 'qualname (file:line)'"""
    name = getattr(fn, "__qualname__", None) or getattr(fn, "__name__", None)
    if name is None:
        name = f"{type(fn).__qualname__} instance"
    try:
        source_file = inspect.getsourcefile(fn)
        _, line_number = inspect.getsourcelines(fn)
    except (TypeError, OSError):
        return name
    if source_file is None:
        return name
    return f"{name} ({source_file}:{line_number})"


def _describe_provider(provider: Provider) -> str:
    if provider.is_seed:
        return "declared as a seed"
    return _describe_callable(provider.fn)


def _suggest_key(key: Any, known: Iterable[Any]) -> str:
    """Return a suggestion for ``key``, or an empty string: a close match among the
    name keys, or the same name registered under the other kind
    """
    known = list(known)
    names = {known_key: known_key for known_key in known if isinstance(known_key, str)}
    types = {_format_key(known_key): known_key for known_key in known if not isinstance(known_key, str)}
    if isinstance(key, str):
        matches = difflib.get_close_matches(key, names, n=3)
        if matches:
            return "\n  did you mean: " + ", ".join(repr(match) for match in matches) + "?"
        other, lookup = types, key
    else:
        other, lookup = names, _format_key(key)
    by_lower = {candidate.lower(): candidate for candidate in other}
    for match in difflib.get_close_matches(lookup.lower(), by_lower, n=1):
        found = other[by_lower[match]]
        if isinstance(found, str):
            return f"\n  but a similar provider with the string key {_format_key(found)} was found"
        return f"\n  but a similar provider with the type key {_format_key(found)} was found"
    return ""
