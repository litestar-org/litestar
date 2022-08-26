from pydantic_openapi_schema.v3_1_0 import Components, Example, Header

from starlite import OpenAPIConfig


def test_merged_components_correct() -> None:
    components_one = Components(headers={"one": Header()})
    components_two = Components(headers={"two": Header()})
    components_three = Components(examples={"example-one": Example(summary="an example")})
    config = OpenAPIConfig(
        title="my title", version="1.0.0", components=[components_one, components_two, components_three]
    )
    openapi = config.to_openapi_schema()
    assert openapi.components.dict(exclude_none=True) == {  # type: ignore[union-attr]
        "examples": {"example-one": {"summary": "an example"}},
        "headers": {
            "one": {
                "name": "",
                "param_in": "header",
                "required": False,
                "deprecated": False,
                "allowEmptyValue": False,
                "explode": False,
                "allowReserved": False,
            },
            "two": {
                "name": "",
                "param_in": "header",
                "required": False,
                "deprecated": False,
                "allowEmptyValue": False,
                "explode": False,
                "allowReserved": False,
            },
        },
    }
