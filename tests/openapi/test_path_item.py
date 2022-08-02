from typing import cast

import pytest

from starlite import HTTPRoute, Starlite
from starlite.openapi.path_item import create_path_item
from starlite.utils import find_index
from tests.openapi.utils import PersonController


@pytest.fixture
def route() -> HTTPRoute:
    app = Starlite(route_handlers=[PersonController], openapi_config=None)
    index = find_index(app.routes, lambda x: x.path_format == "/{service_id}/person/{person_id}")
    return cast("HTTPRoute", app.routes[index])


def test_create_path_item(route: HTTPRoute) -> None:
    schema = create_path_item(route=route, create_examples=True, plugins=[], use_handler_docstrings=False)
    assert schema.delete
    assert schema.delete.operationId == "Delete Person"
    assert schema.get
    assert schema.get.operationId == "Get Person By Id"
    assert schema.patch
    assert schema.patch.operationId == "Partial Update Person"
    assert schema.put
    assert schema.put.operationId == "Update Person"


def test_create_path_item_use_handler_docstring_false(route: HTTPRoute) -> None:
    schema = create_path_item(route=route, create_examples=True, plugins=[], use_handler_docstrings=False)
    assert schema.get
    assert schema.get.description is None
    assert schema.patch
    assert schema.patch.description == "Description in decorator"


def test_create_path_item_use_handler_docstring_true(route: HTTPRoute) -> None:
    schema = create_path_item(route=route, create_examples=True, plugins=[], use_handler_docstrings=True)
    assert schema.get
    assert schema.get.description == "Description in docstring"
    assert schema.patch
    assert schema.patch.description == "Description in decorator"
