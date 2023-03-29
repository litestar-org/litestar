from typing import Optional

from hypothesis import given
from hypothesis import strategies as st
from starlette.exceptions import HTTPException as StarletteHTTPException

from starlite.enums import MediaType
from starlite.exceptions import (
    HTTPException,
    ImproperlyConfiguredException,
    MissingDependencyException,
    StarliteException,
    ValidationException,
)
from starlite.middleware.exceptions.middleware import create_exception_response
from starlite.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR


@given(detail=st.one_of(st.none(), st.text()))
def test_starlite_exception_repr(detail: Optional[str]) -> None:
    result = StarliteException(detail=detail)  # type: ignore
    assert result.detail == detail
    if detail:
        assert result.__repr__() == f"{result.__class__.__name__} - {result.detail}"
    else:
        assert result.__repr__() == result.__class__.__name__


def test_starlite_exception_str() -> None:
    result = StarliteException("an unknown exception occurred")
    assert str(result) == "an unknown exception occurred"

    result = StarliteException(detail="an unknown exception occurred")
    assert str(result) == "an unknown exception occurred"

    result = StarliteException(200, detail="an unknown exception occurred")
    assert str(result) == "200 an unknown exception occurred"


def test_http_exception_str() -> None:
    exc = HTTPException("message")
    assert str(exc) == "500: message"


@given(status_code=st.integers(min_value=400, max_value=404), detail=st.one_of(st.none(), st.text()))
def test_http_exception(status_code: int, detail: Optional[str]) -> None:
    assert HTTPException().status_code == HTTP_500_INTERNAL_SERVER_ERROR
    result = HTTPException(status_code=status_code, detail=detail or "")
    assert isinstance(result, StarliteException)
    assert result.__repr__() == f"{result.status_code} - {result.__class__.__name__} - {result.detail}"
    assert str(result) == f"{result.status_code}: {result.detail}".strip()


@given(detail=st.one_of(st.none(), st.text()))
def test_improperly_configured_exception(detail: Optional[str]) -> None:
    result = ImproperlyConfiguredException(detail=detail or "")
    assert result.__repr__() == f"{HTTP_500_INTERNAL_SERVER_ERROR} - {result.__class__.__name__} - {result.detail}"
    assert isinstance(result, HTTPException)
    assert isinstance(result, ValueError)


def test_validation_exception() -> None:
    result = ValidationException()
    assert result.__repr__() == f"{HTTP_400_BAD_REQUEST} - {result.__class__.__name__} - {result.detail}"
    assert isinstance(result, HTTPException)
    assert isinstance(result, ValueError)


def test_create_exception_response_utility_starlite_http_exception() -> None:
    exc = HTTPException(detail="starlite http exception", status_code=HTTP_400_BAD_REQUEST, extra=["any"])
    response = create_exception_response(exc)
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.media_type == MediaType.JSON
    assert response.body == b'{"status_code":400,"detail":"starlite http exception","extra":["any"]}'


def test_create_exception_response_utility_starlette_http_exception() -> None:
    exc = StarletteHTTPException(detail="starlette http exception", status_code=HTTP_400_BAD_REQUEST)
    response = create_exception_response(exc)
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.media_type == MediaType.JSON
    assert response.body == b'{"status_code":400,"detail":"starlette http exception"}'


def test_create_exception_response_utility_non_http_exception() -> None:
    exc = RuntimeError("yikes")
    response = create_exception_response(exc)
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.media_type == MediaType.JSON
    assert response.body == b'{"status_code":500,"detail":"RuntimeError(\'yikes\')"}'


def test_missing_dependency_exception() -> None:
    exc = MissingDependencyException("some_package")
    expected = (
        "Package 'some_package' is not installed but required. You can install it by running 'pip install "
        "starlite[some_package]' to install starlite with the required extra or 'pip install some_package' to install "
        "the package separately"
    )
    assert str(exc) == expected


def test_missing_dependency_exception_differing_package_name() -> None:
    exc = MissingDependencyException("some_package", "install_via_this")
    expected = (
        "Package 'some_package' is not installed but required. You can install it by running 'pip install "
        "starlite[install_via_this]' to install starlite with the required extra or 'pip install install_via_this' to "
        "install the package separately"
    )

    assert str(exc) == expected
