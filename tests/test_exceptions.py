from hypothesis import given
from hypothesis import strategies as st
from starlette.exceptions import HTTPException as StarletteHTTPException

from starlite.exceptions import ConfigurationException, HTTPException, StarLiteException


@given(message=st.one_of(st.none(), st.text()))
def test_starlite_exception(message):
    result = StarLiteException(message=message)
    assert result.message == message
    if message:
        assert result.__repr__() == f"{result.__class__.__name__} - {result.message}"
    else:
        assert result.__repr__() == result.__class__.__name__


@given(message=st.one_of(st.none(), st.text()))
def test_configuration_exception(message):
    result = ConfigurationException(message=message)
    if message:
        assert result.__repr__() == f"{result.__class__.__name__} - {result.message}"
    else:
        assert result.__repr__() == result.__class__.__name__


@given(status_code=st.integers(min_value=400, max_value=404), message=st.one_of(st.none(), st.text()))
def test_http_exception(status_code, message):
    result = HTTPException(status_code=status_code, message=message)
    assert isinstance(result, StarLiteException)
    assert isinstance(result, StarletteHTTPException)
    assert result.__repr__() == f"{result.status_code} - {result.__class__.__name__} - {result.message}"
