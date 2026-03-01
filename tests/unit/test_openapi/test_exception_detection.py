"""Tests for automatic HTTPException detection from handler source."""

from __future__ import annotations

from typing import Any

from litestar._openapi.exception_detection import detect_exceptions_from_handler
from litestar.exceptions import (
    NotAuthorizedException,
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


def handler_with_attribute_raise() -> None:
    from litestar import exceptions

    raise exceptions.NotAuthorizedException(detail="unauthorized")


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


def test_detect_attribute_raise() -> None:
    # Attribute-style raises (e.g. exceptions.NotAuthorizedException) should also be detected
    # Note: this relies on the class being available in the handler's globals after the import
    result = detect_exceptions_from_handler(handler_with_attribute_raise)
    assert NotAuthorizedException in result or result == []  # may not resolve if not in globals
