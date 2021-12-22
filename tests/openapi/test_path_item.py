from starlite import Router
from starlite.openapi.path_item import create_path_item
from starlite.utils import find_index
from tests.openapi.utils import PersonController, default_config


def test_create_path_item():
    router = Router(path="", route_handlers=[PersonController])
    index = find_index(router.routes, lambda x: x.path_format == "/{service_id}/person/{person_id}")
    route = router.routes[index]
    schema = create_path_item(route=route, config=default_config)
    assert schema.delete
    assert schema.delete.operationId == "delete_person"
    assert schema.get
    assert schema.get.operationId == "get_person_by_id"
    assert schema.patch
    assert schema.patch.operationId == "partial_update_person"
    assert schema.put
    assert schema.put.operationId == "update_person"
