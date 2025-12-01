import pytest
from hypothesis import given
from hypothesis import strategies as st
from starlette.exceptions import HTTPException as StarletteHTTPException

from litestar import get
from litestar.enums import MediaType
from litestar.exceptions import (
    HTTPException,
    ImproperlyConfiguredException,
    LitestarException,
    MissingDependencyException,
    ValidationException,
)
from litestar.exceptions.responses import create_exception_response
from litestar.exceptions.responses._debug_response import (
    create_html_response_content,
    create_plain_text_response_content,
)
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import RequestFactory, create_test_client


class CustomLitestarException(LitestarException):
    detail = "Custom Exception"


class CustomHTTPException(HTTPException):
    detail = "Custom HTTP Exception"


class CustomHTTPExceptionWithExtra(HTTPException):
    status_code = HTTP_400_BAD_REQUEST
    extra = {"key": "value"}


class CustomHTTPExceptionWithHeaders(HTTPException):
    status_code = HTTP_400_BAD_REQUEST
    headers = {"X-Custom-Header": "value"}


@given(detail=st.text())
def test_litestar_exception_detail(detail: str) -> None:
    for result in LitestarException(detail=detail), LitestarException(detail):
        assert result.detail == detail


@given(detail=st.text())
def test_custom_litestar_exception_detail(detail: str) -> None:
    for result in CustomLitestarException(detail=detail), CustomLitestarException(detail):
        assert result.detail == (detail or "Custom Exception")


@given(detail=st.text())
@pytest.mark.parametrize("ex_type", [LitestarException, CustomLitestarException])
def test_litestar_exception_repr(ex_type: type[LitestarException], detail: str) -> None:
    for result in ex_type(detail), ex_type(detail=detail):
        if result.detail:
            assert repr(result) == f"{result.__class__.__name__} - {result.detail}"
        else:
            assert repr(result) == result.__class__.__name__


@given(detail=st.text())
@pytest.mark.parametrize("ex_type", [LitestarException, CustomLitestarException])
def test_litestar_exception_str(ex_type: type[LitestarException], detail: str) -> None:
    for result in ex_type(detail), ex_type(detail=detail):
        assert str(result) == result.detail.strip()

    result = ex_type(200, detail=detail)
    assert str(result) == f"200 {detail}".strip()


@given(detail=st.text())
def test_http_exception_detail(detail: str) -> None:
    for result in HTTPException(detail=detail), HTTPException(detail):
        assert result.detail == (detail or "Internal Server Error")


@given(detail=st.text())
def test_custom_http_exception_detail(detail: str) -> None:
    for result in CustomHTTPException(detail=detail), CustomHTTPException(detail):
        assert result.detail == (detail or "Custom HTTP Exception")


@given(status_code=st.integers(min_value=400, max_value=404), detail=st.text())
@pytest.mark.parametrize("ex_type", [HTTPException, CustomHTTPException])
def test_http_exception(ex_type: type[HTTPException], status_code: int, detail: str) -> None:
    assert ex_type().status_code == HTTP_500_INTERNAL_SERVER_ERROR
    for result in ex_type(detail, status_code=status_code), ex_type(detail=detail, status_code=status_code):
        assert isinstance(result, LitestarException)
        assert repr(result) == f"{result.status_code} - {result.__class__.__name__} - {result.detail}"
        assert str(result) == f"{result.status_code}: {result.detail}".strip()


@given(detail=st.text())
def test_improperly_configured_exception(detail: str) -> None:
    result = ImproperlyConfiguredException(detail=detail)
    assert repr(result) == f"{HTTP_500_INTERNAL_SERVER_ERROR} - {result.__class__.__name__} - {result.detail}"
    assert isinstance(result, HTTPException)
    assert isinstance(result, ValueError)


def test_validation_exception() -> None:
    result = ValidationException()
    assert repr(result) == f"{HTTP_400_BAD_REQUEST} - {result.__class__.__name__} - {result.detail}"
    assert isinstance(result, HTTPException)
    assert isinstance(result, ValueError)


@pytest.mark.parametrize("media_type", [MediaType.JSON, MediaType.TEXT])
def test_create_exception_response_utility_litestar_http_exception(media_type: MediaType) -> None:
    exc = HTTPException(detail="litestar http exception", status_code=HTTP_400_BAD_REQUEST, extra=["any"])
    request = RequestFactory(handler_kwargs={"media_type": media_type}).get()
    response = create_exception_response(request=request, exc=exc)
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.media_type == media_type
    if media_type == MediaType.JSON:
        assert response.content == {"status_code": 400, "detail": "litestar http exception", "extra": ["any"]}
    else:
        assert response.content == b'{"status_code":400,"detail":"litestar http exception","extra":["any"]}'


@pytest.mark.parametrize("media_type", [MediaType.JSON, MediaType.TEXT])
def test_create_exception_response_utility_starlette_http_exception(media_type: MediaType) -> None:
    @get("/", media_type=media_type)
    def handler() -> str:
        raise StarletteHTTPException(status_code=400)

    with create_test_client(handler) as client:
        response = client.get("/", headers={"Accept": media_type})
        assert response.json() == {"status_code": 400, "detail": "Bad Request"}


@pytest.mark.parametrize("media_type", [MediaType.JSON, MediaType.TEXT])
def test_create_exception_response_utility_non_http_exception(media_type: MediaType) -> None:
    exc = RuntimeError("yikes")
    request = RequestFactory(handler_kwargs={"media_type": media_type}).get()
    response = create_exception_response(request=request, exc=exc)
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.media_type == media_type
    if media_type == MediaType.JSON:
        assert response.content == {"status_code": 500, "detail": "Internal Server Error"}
    else:
        assert response.content == b'{"status_code":500,"detail":"Internal Server Error"}'


def test_missing_dependency_exception() -> None:
    exc = MissingDependencyException("some_package")
    expected = (
        "Package 'some_package' is not installed but required. You can install it by running `pip install "
        "'litestar[some_package]'` to install litestar with the required extra or 'pip install some_package' to install "
        "the package separately"
    )
    assert str(exc) == expected


def test_missing_dependency_exception_differing_package_name() -> None:
    exc = MissingDependencyException("some_package", "install_via_this", "other-extra")
    expected = (
        "Package 'some_package' is not installed but required. You can install it by running `pip install "
        "'litestar[other-extra]'` to install litestar with the required extra or 'pip install install_via_this' to "
        "install the package separately"
    )

    assert str(exc) == expected


@pytest.mark.parametrize("media_type", (MediaType.HTML, MediaType.JSON, MediaType.TEXT))
def test_default_exception_handling_of_internal_server_errors(media_type: MediaType) -> None:
    @get("/")
    def handler() -> None:
        raise ValueError("internal problem")

    with create_test_client(handler) as client:
        response = client.get("/", headers={"Accept": media_type})
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        if media_type == MediaType.HTML:
            assert response.text.startswith("<!doctype html>")
        elif media_type == MediaType.JSON:
            assert response.json().get("details").startswith("Traceback (most recent call last")
        else:
            assert response.text.startswith("Traceback (most recent call last")


def test_non_litestar_exception_with_status_code_is_500() -> None:
    # https://github.com/litestar-org/litestar/issues/3082
    class MyException(Exception):
        status_code: int = 400

    @get("/")
    def handler() -> None:
        raise MyException("hello")

    with create_test_client([handler]) as client:
        assert client.get("/").status_code == 500


def test_non_litestar_exception_with_detail_is_not_included() -> None:
    # https://github.com/litestar-org/litestar/issues/3082
    class MyException(Exception):
        status_code: int = 400
        detail: str = "hello"

    @get("/")
    def handler() -> None:
        raise MyException()

    with create_test_client([handler], debug=False) as client:
        assert client.get("/", headers={"Accept": MediaType.JSON}).json().get("detail") == "Internal Server Error"


def test_http_exception_with_class_var_extra() -> None:
    @get("/")
    def handler() -> None:
        raise CustomHTTPExceptionWithExtra("hello")

    with create_test_client([handler], debug=False) as client:
        assert client.get("/").json() == {
            "extra": {"key": "value"},
            "status_code": 400,
            "detail": "hello",
        }


def test_http_exception_with_class_var_extra_explicit_none() -> None:
    @get("/")
    def handler() -> None:
        raise CustomHTTPExceptionWithExtra("hello", extra=None)

    with create_test_client([handler], debug=False) as client:
        assert client.get("/").json() == {
            "status_code": 400,
            "detail": "hello",
        }


def test_http_exception_with_class_var_headers() -> None:
    @get("/")
    def handler() -> None:
        raise CustomHTTPExceptionWithHeaders("hello")

    with create_test_client([handler], debug=False) as client:
        response = client.get("/")
        assert response.headers["X-Custom-Header"] == "value"
        assert response.json() == {
            "status_code": 400,
            "detail": "hello",
        }


def test_http_exception_with_class_var_headers_explicit_none() -> None:
    @get("/")
    def handler() -> None:
        raise CustomHTTPExceptionWithHeaders("hello", headers=None)

    with create_test_client([handler], debug=False) as client:
        response = client.get("/")
        assert "X-Custom-Header" not in response.headers
        assert response.json() == {
            "status_code": 400,
            "detail": "hello",
        }


def test_debug_html_response_contains_copy_traceback_elements() -> None:
    """Test that debug HTML response includes copy-and-paste traceback UI elements."""

    @get("/")
    def handler() -> None:
        raise ValueError("test error")

    with create_test_client([handler], debug=True) as client:
        response = client.get("/", headers={"Accept": MediaType.HTML})
        html = response.text

        # Verify copy button exists (always visible)
        assert 'id="copyBtn"' in html
        assert "copyTraceback()" in html
        assert "Copy traceback to clipboard" in html

        # Verify toggle button exists
        assert 'id="toggleView"' in html
        assert "toggleTracebackView()" in html
        assert "Plaintext view" in html

        # Verify traceback views exist
        assert 'id="browserTraceback"' in html
        assert 'id="pastebinTraceback"' in html
        assert 'id="traceback_area"' in html

        # Verify plain text traceback is included (escaped)
        assert "Traceback (most recent call last)" in html
        assert "ValueError" in html


def test_debug_html_response_contains_javascript_functions() -> None:
    """Test that debug HTML response includes the toggle and copy JavaScript functions."""

    @get("/")
    def handler() -> None:
        raise ValueError("test error")

    with create_test_client([handler], debug=True) as client:
        response = client.get("/", headers={"Accept": MediaType.HTML})
        html = response.text

        # Verify JavaScript functions are included
        assert "function toggleTracebackView()" in html
        assert "function copyTraceback()" in html
        assert "navigator.clipboard.writeText" in html


def test_debug_html_response_contains_css_styles() -> None:
    """Test that debug HTML response includes the CSS styles for traceback controls."""

    @get("/")
    def handler() -> None:
        raise ValueError("test error")

    with create_test_client([handler], debug=True) as client:
        response = client.get("/", headers={"Accept": MediaType.HTML})
        html = response.text

        # Verify CSS styles are included
        assert ".traceback-controls" in html
        assert "#traceback_area" in html


def test_create_html_response_content_includes_plain_text_traceback() -> None:
    """Test that create_html_response_content includes escaped plain text traceback."""
    request = RequestFactory().get()

    try:
        raise ValueError("test exception message")
    except ValueError as exc:
        html = create_html_response_content(exc, request)

        # Verify plain text traceback content is present and escaped
        assert "Traceback (most recent call last)" in html
        assert "ValueError: test exception message" in html
        assert 'id="traceback_area"' in html


def test_create_plain_text_response_content_format() -> None:
    """Test that create_plain_text_response_content produces proper traceback format."""
    try:
        raise ValueError("test exception")
    except ValueError as exc:
        text = create_plain_text_response_content(exc)

        assert text.startswith("Traceback (most recent call last)")
        assert "ValueError: test exception" in text
