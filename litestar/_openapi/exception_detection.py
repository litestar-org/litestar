"""Automatic detection of HTTPException subclasses raised in route handlers."""

from __future__ import annotations

import inspect
import io
import textwrap
import tokenize
from typing import Any, Callable

from litestar.exceptions.http_exceptions import HTTPException

__all__ = ("detect_exceptions_from_handler",)


def _resolve_callable(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Resolve the underlying function from various callable types.

    Handles bound methods, classmethods, staticmethods, and wrapped callables
    so that :func:`inspect.getsource` and ``__globals__`` work correctly.
    """
    fn = inspect.unwrap(fn)
    # bound/unbound methods, classmethods, staticmethods
    fn = getattr(fn, "__func__", fn)
    # classes: inspect __init__ for raised exceptions
    if isinstance(fn, type):
        fn = fn.__init__  # type: ignore[misc]
    return fn


def detect_exceptions_from_handler(fn: Callable[..., Any]) -> list[type[HTTPException]]:
    """Detect HTTPException subclasses raised in a handler function via token inspection.

    Scans the handler's source code for ``raise`` tokens and resolves the following
    name against the handler's global namespace.  Only subclasses of
    :class:`HTTPException <litestar.exceptions.http_exceptions.HTTPException>` are returned.

    Uses :mod:`tokenize` instead of :mod:`ast` for lower overhead.

    Supports plain functions, bound/unbound methods, classmethods, staticmethods,
    and classes (inspects ``__init__``).

    Args:
        fn: The route handler callable to inspect.

    Returns:
        A list of HTTPException subclass types found in ``raise`` statements.
    """
    fn = _resolve_callable(fn)

    try:
        source = inspect.getsource(fn)
        source = textwrap.dedent(source)
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (OSError, TypeError, tokenize.TokenError):
        return []

    exception_names: set[str] = set()

    for i, tok in enumerate(tokens):
        if tok.type != tokenize.NAME or tok.string != "raise":
            continue

        # Walk forward past whitespace/newline tokens to find the exception name
        j = i + 1
        while j < len(tokens) and tokens[j].type in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.COMMENT):
            j += 1

        if j >= len(tokens) or tokens[j].type != tokenize.NAME:
            continue

        name = tokens[j].string

        # Handle dotted paths: ``module.ExceptionClass``
        k = j + 1
        while k + 1 < len(tokens) and tokens[k].type == tokenize.OP and tokens[k].string == ".":
            if tokens[k + 1].type == tokenize.NAME:
                name = tokens[k + 1].string
                k += 2
            else:
                break

        exception_names.add(name)

    if not exception_names:
        return []

    fn_globals = getattr(fn, "__globals__", {})
    detected: list[type[HTTPException]] = []

    for name in exception_names:
        cls = fn_globals.get(name)
        if cls is not None and isinstance(cls, type) and issubclass(cls, HTTPException):
            detected.append(cls)

    return detected
