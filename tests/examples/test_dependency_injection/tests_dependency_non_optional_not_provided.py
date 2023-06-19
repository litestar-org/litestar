import pytest
from docs.examples.dependency_injection import dependency_non_optional_not_provided

from litestar import Litestar
from litestar.exceptions import ImproperlyConfiguredException


def test_route_returns_internal_server_error() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[dependency_non_optional_not_provided.hello_world])
