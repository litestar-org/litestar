from starlite import Starlite
from starlite.openapi.path_item import create_path_item
from starlite.utils import find_index
from tests.openapi.utils import PersonController


def test_create_path_item():
    app = Starlite(route_handlers=[PersonController], openapi_config=None)
    index = find_index(app.routes, lambda x: x.path_format == "/{service_id}/person/{person_id}")
    route = app.routes[index]
    schema = create_path_item(route=route, create_examples=True)
    assert schema.delete
    assert schema.delete.operationId == "delete_person"
    assert schema.get
    assert schema.get.operationId == "get_person_by_id"
    assert schema.patch
    assert schema.patch.operationId == "partial_update_person"
    assert schema.put
    assert schema.put.operationId == "update_person"
