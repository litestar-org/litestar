from typing import Callable, cast

from starlite import Starlite
from starlite.openapi.enums import OpenAPIType
from starlite.openapi.parameters import create_parameters
from starlite.signature import model_function_signature
from starlite.utils import find_index
from tests.openapi.utils import PersonController


def test_create_parameters() -> None:
    app = Starlite(route_handlers=[PersonController])
    index = find_index(app.routes, lambda x: x.path_format == "/{service_id}/person")
    route = app.routes[index]
    route_handler = PersonController.get_persons
    parameters = create_parameters(
        route_handler=route_handler,
        handler_fields=model_function_signature(fn=cast(Callable, route_handler.fn), plugins=[]).__fields__,
        path_parameters=route.path_parameters,
        generate_examples=True,
    )
    assert len(parameters) == 9
    page, name, page_size, service_id, from_date, to_date, gender, secret_header, cookie_value = tuple(parameters)
    assert service_id.name == "service_id"
    assert service_id.param_in == "path"
    assert service_id.param_schema.type == OpenAPIType.INTEGER
    assert service_id.required
    assert service_id.param_schema.examples
    assert page.param_in == "query"
    assert page.name == "page"
    assert page.param_schema.type == OpenAPIType.INTEGER
    assert page.required
    assert page.param_schema.examples
    assert page_size.param_in == "query"
    assert page_size.name == "pageSize"
    assert page_size.param_schema.type == OpenAPIType.INTEGER
    assert page_size.required
    assert page_size.description == "Page Size Description"
    assert page_size.param_schema.examples[0].value == 1
    assert name.param_in == "query"
    assert name.name == "name"
    assert len(name.param_schema.oneOf) == 2
    assert name.required
    assert name.param_schema.examples
    assert from_date.param_in == "query"
    assert from_date.name == "from_date"
    assert len(from_date.param_schema.oneOf) == 4
    assert not from_date.required
    assert from_date.param_schema.examples
    assert to_date.param_in == "query"
    assert to_date.name == "to_date"
    assert len(to_date.param_schema.oneOf) == 4
    assert not to_date.required
    assert to_date.param_schema.examples
    assert gender.param_in == "query"
    assert gender.name == "gender"
    assert gender.param_schema.dict(exclude_none=True) == {
        "oneOf": [
            {"type": "null"},
            {"type": "string", "enum": ["M", "F", "O", "A"]},
            {"items": [{"type": "string", "enum": ["M", "F", "O", "A"]}], "type": "array"},
        ],
        "examples": [{"value": "M"}, {"value": ["M", "O"]}],
    }
    assert not gender.required
    assert secret_header.param_in == "header"
    assert secret_header.param_schema.type == OpenAPIType.STRING
    assert secret_header.required
    assert secret_header.param_schema.examples
    assert cookie_value.param_in == "cookie"
    assert cookie_value.param_schema.type == OpenAPIType.INTEGER
    assert cookie_value.required
    assert cookie_value.param_schema.examples
