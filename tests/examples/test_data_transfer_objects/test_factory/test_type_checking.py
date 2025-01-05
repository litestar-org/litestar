import pytest

from litestar.exceptions.dto_exceptions import InvalidAnnotationException


def test_should_raise_error_on_route_registration() -> None:
    with pytest.raises(InvalidAnnotationException):
        from docs.examples.data_transfer_objects.factory.type_checking import app  # noqa: F401
