import pytest

from starlite import ImproperlyConfiguredException, Starlite, get


def test_register_validation_duplicate_handlers_for_same_route_and_method() -> None:
    @get(path="/first")
    def first_route_handler() -> None:
        pass

    @get(path="/first")
    def second_route_handler() -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[first_route_handler, second_route_handler])
