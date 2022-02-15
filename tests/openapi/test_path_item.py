from typing import cast

from starlite import HTTPRoute, Starlite
from starlite.openapi.path_item import create_path_item
from starlite.utils import find_index
from tests.openapi.utils import PersonController


def test_create_path_item() -> None:
    app = Starlite(route_handlers=[PersonController], openapi_config=None)
    index = find_index(app.routes, lambda x: x.path_format == "/{service_id}/person/{person_id}")
    route = cast(HTTPRoute, app.routes[index])
    schema = create_path_item(route=route, create_examples=True)
    assert schema.delete
    assert schema.delete.operationId == "Delete Person"
    assert schema.get
    assert schema.get.operationId == "Get Person By Id"
    assert schema.patch
    assert schema.patch.operationId == "Partial Update Person"
    assert schema.put
    assert schema.put.operationId == "Update Person"
