"""Automatic detection of HTTPException subclasses raised in route handlers."""

from __future__ import annotations

import ast
import inspect
import textwrap
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from litestar.exceptions.http_exceptions import HTTPException

__all__ = ("detect_exceptions_from_handler",)


def detect_exceptions_from_handler(fn: Callable[..., Any]) -> list[type[HTTPException]]:
    """Detect HTTPException subclasses raised in a handler function via AST inspection.

    Scans the handler's source code for ``raise`` statements and resolves exception
    class names against the handler's global namespace. Only direct subclasses of
    :class:`HTTPException <litestar.exceptions.http_exceptions.HTTPException>` are returned.

    Args:
        fn: The route handler callable to inspect.

    Returns:
        A list of HTTPException subclass types found in ``raise`` statements.
    """
    from litestar.exceptions.http_exceptions import HTTPException

    try:
        source = inspect.getsource(fn)
        source = textwrap.dedent(source)
        tree = ast.parse(source)
    except (OSError, TypeError, IndentationError, SyntaxError):
        return []

    exception_names: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue

        exc_node = node.exc
        # Handle: raise SomeException(...)
        if isinstance(exc_node, ast.Call):
            func = exc_node.func
            if isinstance(func, ast.Name):
                exception_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                exception_names.add(func.attr)
        # Handle: raise SomeException (no call)
        elif isinstance(exc_node, ast.Name):
            exception_names.add(exc_node.id)

    if not exception_names:
        return []

    fn_globals = getattr(fn, "__globals__", {})
    detected: list[type[HTTPException]] = []

    for name in exception_names:
        cls = fn_globals.get(name)
        if cls is not None and isinstance(cls, type) and issubclass(cls, HTTPException):
            detected.append(cls)

    return detected
