"""Tests for automatic HTTPException detection from handler source."""

from __future__ import annotations

from litestar._openapi.exception_detection import detect_exceptions_from_handler
from litestar.exceptions import (
    NotFoundException,
    PermissionDeniedException,
)


def handler_with_single_exception() -> None:
    raise NotFoundException(detail="not found")


def handler_with_multiple_exceptions(force_perm_fail: bool = False) -> None:
    if force_perm_fail:
        raise PermissionDeniedException
    raise NotFoundException(detail="not found")


def handler_with_no_exceptions() -> str:
    return "hello"


def handler_with_non_http_exception() -> None:
    raise ValueError("bad value")


def handler_with_bare_raise() -> None:
    try:
        pass
    except Exception:
        raise


def test_detect_single_exception() -> None:
    result = detect_exceptions_from_handler(handler_with_single_exception)
    assert result == [NotFoundException]


def test_detect_multiple_exceptions() -> None:
    result = detect_exceptions_from_handler(handler_with_multiple_exceptions)
    assert set(result) == {PermissionDeniedException, NotFoundException}


def test_detect_no_exceptions() -> None:
    result = detect_exceptions_from_handler(handler_with_no_exceptions)
    assert result == []


def test_detect_ignores_non_http_exceptions() -> None:
    result = detect_exceptions_from_handler(handler_with_non_http_exception)
    assert result == []


def test_detect_graceful_fallback_for_uninspectable() -> None:
    # Built-in functions have no inspectable source
    result = detect_exceptions_from_handler(len)
    assert result == []


def test_detect_bare_raise_ignored() -> None:
    # A bare raise (no exception class) should not cause errors
    result = detect_exceptions_from_handler(handler_with_bare_raise)
    assert result == []


def handler_with_subscript_call_raise() -> None:
    exc_classes = [NotFoundException]
    raise exc_classes[0](detail="not found")


def handler_with_subscript_raise() -> None:
    errors = [NotFoundException(detail="not found")]
    raise errors[0]


def test_detect_complex_call_func_ignored() -> None:
    # When func is ast.Subscript (not Name or Attribute), it's safely skipped.
    result = detect_exceptions_from_handler(handler_with_subscript_call_raise)
    assert result == []


def test_detect_subscript_raise_ignored() -> None:
    # When exc_node is ast.Subscript (not Call or Name), it's safely skipped.
    result = detect_exceptions_from_handler(handler_with_subscript_raise)
    assert result == []


def test_detect_attribute_style_raise() -> None:
    # Attribute-style raises (e.g. module.SomeException) are parsed via ast.Attribute.
    # The attr name is extracted and resolved against fn_globals.
    from litestar.exceptions import NotFoundException as _NotFoundException

    def _handler() -> None:
        from litestar import exceptions

        raise exceptions.NotFoundException(detail="not found")

    # Inject NotFoundException into the handler's module globals so it can be resolved
    _handler.__globals__["NotFoundException"] = _NotFoundException
    result = detect_exceptions_from_handler(_handler)
    assert _NotFoundException in result
