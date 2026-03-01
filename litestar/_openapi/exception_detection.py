"""Automatic detection of HTTPException subclasses raised in route handlers."""

from __future__ import annotations

import ast
import inspect
import textwrap
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
    if hasattr(fn, "__func__"):
        fn = fn.__func__
    # classes: inspect __init__ for raised exceptions
    if isinstance(fn, type):
        fn = fn.__init__  # type: ignore[misc]
    return fn


def detect_exceptions_from_handler(fn: Callable[..., Any]) -> list[type[HTTPException]]:
    """Detect HTTPException subclasses raised in a handler function via AST inspection.

    Scans the handler's source code for ``raise`` statements and resolves exception
    class names against the handler's global namespace. Only direct subclasses of
    :class:`HTTPException <litestar.exceptions.http_exceptions.HTTPException>` are returned.

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
