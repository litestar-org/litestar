from hypothesis import given
from hypothesis import strategies as st
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from starlite.exceptions import (
    HTTPException,
    ImproperlyConfiguredException,
    StarLiteException,
)


@given(detail=st.one_of(st.none(), st.text()))
def test_starlite_exception(detail):
    result = StarLiteException(detail=detail)
    assert result.detail == detail
    if detail:
        assert result.__repr__() == f"{result.__class__.__name__} - {result.detail}"
    else:
        assert result.__repr__() == result.__class__.__name__


@given(status_code=st.integers(min_value=400, max_value=404), detail=st.one_of(st.none(), st.text()))
def test_http_exception(status_code, detail):
    result = HTTPException(status_code=status_code, detail=detail)
    assert isinstance(result, StarLiteException)
    assert isinstance(result, StarletteHTTPException)
    assert result.__repr__() == f"{result.status_code} - {result.__class__.__name__} - {result.detail}"


@given(detail=st.one_of(st.none(), st.text()))
def test_configuration_exception(detail):
    result = ImproperlyConfiguredException(detail=detail)
    assert result.__repr__() == f"{HTTP_500_INTERNAL_SERVER_ERROR} - {result.__class__.__name__} - {result.detail}"
