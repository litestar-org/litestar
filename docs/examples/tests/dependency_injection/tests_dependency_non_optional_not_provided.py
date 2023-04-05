import pytest

from examples.dependency_injection import dependency_non_optional_not_provided
from starlite import Starlite
from starlite.exceptions import ImproperlyConfiguredException


def test_route_returns_internal_server_error() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[dependency_non_optional_not_provided.hello_world])
