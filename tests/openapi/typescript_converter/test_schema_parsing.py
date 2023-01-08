from pydantic_openapi_schema.v3_1_0 import Schema

from starlite.openapi.enums import OpenAPIType
from starlite.openapi.typescript_converter.schema_parsing import parse_schema
from starlite.openapi.typescript_converter.types import (
    TypeScriptAnonymousInterface,
    TypeScriptArray,
    TypeScriptInterface,
    TypeScriptIntersection,
    TypeScriptLiteral,
    TypeScriptPrimitive,
    TypeScriptProperty,
    TypeScriptUnion,
)

object_schema_1 = Schema(
    type=OpenAPIType.OBJECT,
    properties={
        "first_1": Schema(
            type=OpenAPIType.STRING,
        ),
        "second_1": Schema(type=[OpenAPIType.NUMBER, OpenAPIType.NULL]),
    },
    required=["first_1"],
)

object_schema_2 = Schema(
    type=OpenAPIType.OBJECT,
    properties={
        "first_2": Schema(
            type=OpenAPIType.BOOLEAN,
        ),
        "second_2": Schema(
            type=OpenAPIType.INTEGER,
        ),
    },
    required=["first_2"],
)

ts_string_primitive = TypeScriptPrimitive("string")
ts_intersection = TypeScriptIntersection(types=[TypeScriptPrimitive("string"), TypeScriptPrimitive("number")])
ts_union = TypeScriptUnion(types=[TypeScriptPrimitive("string"), TypeScriptPrimitive("number")])
ts_boolean_literal = TypeScriptLiteral(True)
ts_string_array = TypeScriptArray(ts_string_primitive)
first_prop = TypeScriptProperty(required=True, key="aProp", value=TypeScriptPrimitive("string"))
second_prop = TypeScriptProperty(required=True, key="bProp", value=TypeScriptPrimitive("number"))
ts_named_interface = TypeScriptInterface(name="MyInterface", properties=[first_prop, second_prop])
ts_anonymous_interface = TypeScriptAnonymousInterface(properties=[first_prop, second_prop])


def test_parse_schema_handle_all_of() -> None:
    result = parse_schema(Schema(allOf=[object_schema_1, object_schema_2]))
    assert isinstance(result, TypeScriptIntersection)
    assert (
        result.write()
        == "{\n\tfirst_1: string;\n\tsecond_1: number | null;\n} & {\n\tfirst_2: boolean;\n\tsecond_2: number;\n}"
    )
